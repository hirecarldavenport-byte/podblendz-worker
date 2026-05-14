from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed
from podpal.blending.round_robin import round_robin_blend

from podpal.ai.pipeline import process_clusters

from podpal.audio.ingest import download_episode_audio
from podpal.audio.tts import generate_audio
from podpal.audio.stitch import stitch_blendz

from podpal.boards.board_config import BOARD_CONFIG

router = APIRouter()


# -------------------------------------------------
# ✅ CLEAN TEXT
# -------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# -------------------------------------------------
# ✅ CHUNK SPLITTING
# -------------------------------------------------
def split_into_chunks(text: str, max_len: int = 300):
    sentences = text.split(". ")
    chunks = []
    current = ""

    for s in sentences:
        if len(current) + len(s) < max_len:
            current += s + ". "
        else:
            chunks.append(current.strip())
            current = s + ". "

    if current:
        chunks.append(current.strip())

    return chunks


# -------------------------------------------------
# ✅ MULTI-QUERY ENGINE
# -------------------------------------------------
def get_queries(query: str) -> List[str]:
    q = query.lower()

    if "genetics" in q:
        return [
            "CRISPR gene editing podcast",
            "genomics dna sequencing",
            "biotechnology research podcast",
            "molecular biology genetics discussion",
            "gene mutation research biology podcast"
        ]

    return [query]


# -------------------------------------------------
# ✅ DOMAIN FILTER
# -------------------------------------------------
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    domain_terms = [
        "gene", "dna", "genome", "genetic",
        "crispr", "biology", "biotech",
        "mutation", "molecular", "cell"
    ]

    score = sum(1 for t in domain_terms if t in text)
    return score >= 2


# -------------------------------------------------
# ✅ CLEAN FOR TTS
# -------------------------------------------------
def clean_for_tts(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"http\S+", "", text)

    # ✅ critical: remove non-ascii
    text = text.encode("ascii", "ignore").decode()

    text = re.sub(r"[^a-zA-Z0-9.,!?;:'\"()\-\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# -------------------------------------------------
# ✅ CORE BLEND FUNCTION
# -------------------------------------------------
def run_blend(query: str, target_minutes: int, enable_ai: bool):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n🔍 QUERY: {query}")

    # ---------------- SEARCH ----------------
    feed_urls = []
    for q in get_queries(query):
        try:
            feed_urls.extend(resolve_search_term(q))
        except:
            continue

    feed_urls = list(set(feed_urls))[:30]

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except:
            continue

    episodes_by_feed = {}

    for feed in feeds:
        try:
            rss = fetch_rss_feed(feed.feed_url)
            episodes_by_feed[feed.feed_url] = rss.get("items", [])
        except:
            episodes_by_feed[feed.feed_url] = []

    blended = round_robin_blend(episodes_by_feed, 1, 6)

    # ---------------- FILTER ----------------
    filtered = []

    for ep in blended:
        text = (ep.get("title", "") + " " +
                ep.get("summary", "")).lower()

        if not is_good_domain_text(text):
            continue

        if len(text.split()) < 25:
            continue

        filtered.append(ep)

    # ---------------- FALLBACK ----------------
    if not filtered:
        print("⚠️ fallback scoring")

        scored = []

        for ep in blended:
            text = (ep.get("title", "") + " " +
                    ep.get("summary", "")).lower()

            score = sum(1 for k in [
                "gene", "dna", "biology", "science", "research"
            ] if k in text)

            if score > 0:
                scored.append((score, ep))

        scored.sort(reverse=True, key=lambda x: x[0])
        filtered = [ep for _, ep in scored[:3]]

    blended = filtered[:3]
    print(f"✅ Using {len(blended)} episodes")

    # ---------------- AUDIO DOWNLOAD ----------------
    clip_paths = []

    for ep in blended:
        try:
            audio_url = next(
                (l.get("href") for l in ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None,
            )

            if audio_url:
                filename = download_episode_audio(audio_url)
                if filename:
                    clip_paths.append(str(RAW_DIR / filename))

        except:
            continue

    # ---------------- AI ----------------
    narration_paths = []
    ai_output = None

    # ✅ INTRO
    intro = clean_for_tts(
        f"Welcome to your PodBlendz experience. Today we explore {query}."
    )

    if len(intro.split()) > 5:
        try:
            narration_paths.append(generate_audio(intro))
        except:
            pass

    if enable_ai:
        try:
            segments = []

            for ep in blended:
                raw = ep.get("summary") or ep.get("description")
                cleaned = clean_text(raw)

                if cleaned:
                    segments.extend(split_into_chunks(cleaned)[:2])

            # ✅ remove duplicates
            seen = set()
            unique_segments = []
            for s in segments:
                key = s[:80]
                if key not in seen:
                    seen.add(key)
                    unique_segments.append(s)

            segments = unique_segments

            if segments:
                clusters = [
                    {"id": i + 1, "segments": [seg]}
                    for i, seg in enumerate(segments[:5])
                ]

                ai_output = process_clusters(clusters)

                for c in ai_output:
                    narration = c.get("narration")

                    # 🚫 block bad AI outputs
                    if not narration:
                        continue

                    if "please provide" in narration.lower():
                        continue

                    if len(narration.strip()) < 40:
                        continue

                    safe = clean_for_tts(narration)

                    if len(safe.split()) < 8:
                        continue

                    safe = safe[:1000]

                    try:
                        narration_paths.append(generate_audio(safe))
                    except Exception as e:
                        print("⚠️ Skipping narration:", e)

        except Exception as e:
            print("⚠️ AI error:", e)

    # ---------------- STITCH ----------------
    final_audio = None

    if narration_paths:
        sequence = []

        for i in range(len(narration_paths)):
            sequence.append(narration_paths[i])

            if i < len(clip_paths):
                sequence.append(clip_paths[i])

        if sequence:
            try:
                filename = stitch_blendz(sequence, target_minutes)
                final_audio = f"/audio/final/{filename}"
            except Exception as e:
                print("🔥 Audio error:", e)

    return {
        "query": query,
        "results": blended,
        "ai": ai_output,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
    }