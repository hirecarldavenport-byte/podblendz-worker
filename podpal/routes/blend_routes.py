from fastapi import APIRouter
from typing import List, Optional
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


# ---------------- CLEAN TEXT ----------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------- SPLIT ----------------
def split_into_chunks(text: str, max_len: int = 300):
    sentences = text.split(". ")
    chunks, current = [], ""

    for s in sentences:
        if len(current) + len(s) < max_len:
            current += s + ". "
        else:
            chunks.append(current.strip())
            current = s + ". "

    if current:
        chunks.append(current.strip())

    return chunks


# ---------------- SEARCH QUERIES ----------------
def get_queries(query: str) -> List[str]:
    q = query.lower()

    if "genetics" in q:
        return [
            "crispr gene editing dna podcast",
            "genomics molecular biology podcast",
            "biotech genetics research podcast",
        ]

    return [query]


# ---------------- FILTER (FIXED) ----------------
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    keep_terms = [
        "gene", "dna", "genome", "genomic",
        "biology", "biotech", "crispr",
        "molecular", "cell", "mutation",
        "sequencing", "antibody"
    ]

    bad_terms = [
        "mindset", "spiritual", "relationship",
        "fitness", "self help"
    ]

    if any(b in text for b in bad_terms):
        return False

    # ✅ Much looser → prevents 1-episode problem
    return any(k in text for k in keep_terms)


# ---------------- CLEAN FOR TTS (CRITICAL FIX) ----------------
def clean_for_tts(text: str) -> str:
    if not text:
        return ""

    # ✅ remove TTS-breaking patterns
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"<.*?>", "", text)

    text = text.encode("ascii", "ignore").decode()

    text = re.sub(r"[^a-zA-Z0-9.,!?;:'\"()\-\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def is_valid_tts(text: str) -> bool:
    if not text or len(text) < 60:
        return False

    bad = ["please provide", "subscribe", "visit", "http", "www"]
    return not any(b in text.lower() for b in bad)


# ---------------- CORE FUNCTION ----------------
def run_blend(query: str, target_minutes: int, enable_ai: bool):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n🔍 QUERY: {query}")

    # ---------- SEARCH ----------
    feed_urls = []
    for q in get_queries(query):
        try:
            feed_urls.extend(resolve_search_term(q))
        except:
            continue

    feed_urls = list(set(feed_urls))[:40]

    # ---------- RESOLVE ----------
    feeds = []
    for url in feed_urls:
        try:
            f = resolve_podcast_source(url)
            if f:
                feeds.append(f)
        except:
            continue

    # ---------- FETCH ----------
    episodes_by_feed = {}
    for f in feeds:
        try:
            rss = fetch_rss_feed(f.feed_url)
            episodes_by_feed[f.feed_url] = rss.get("items", [])
        except:
            episodes_by_feed[f.feed_url] = []

    blended = round_robin_blend(episodes_by_feed, 1, 6)

    # ---------- FILTER ----------
    filtered = []
    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

        if is_good_domain_text(text):
            filtered.append(ep)

    if not filtered:
        print("⚠️ fallback")
        filtered = blended[:5]

    blended = filtered[:5]
    print(f"✅ Using {len(blended)} episodes")

    # ---------- AUDIO ----------
    clip_paths = []

    for ep in blended:
        try:
            audio_url = next(
                (l.get("href") for l in ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None
            )

            if audio_url:
                fn = download_episode_audio(audio_url)
                if fn:
                    clip_paths.append(str(RAW_DIR / fn))
        except:
            continue

    # ✅ ensure multiple clips
    if len(clip_paths) < 2:
        print("⚠️ expanding clips")

        for ep in blended:
            try:
                audio_url = next(
                    (l.get("href") for l in ep.get("links", [])
                     if "audio" in l.get("type", "")),
                    None
                )

                if audio_url:
                    fn = download_episode_audio(audio_url)
                    if fn:
                        clip_paths.append(str(RAW_DIR / fn))
            except:
                continue

    # ---------- AI ----------
    narration_paths = []

    if enable_ai:
        try:
            segments = []

            for ep in blended:
                raw = ep.get("summary") or ep.get("description")
                cleaned = clean_text(raw)

                if cleaned:
                    segments.extend(split_into_chunks(cleaned)[:2])

            clusters = [
                {"id": i + 1, "segments": [s]}
                for i, s in enumerate(segments[:5])
            ]

            ai_output = process_clusters(clusters)

            for c in ai_output:
                safe = clean_for_tts(c.get("narration"))

                if not is_valid_tts(safe):
                    continue

                # ✅ domain guard
                if not any(x in safe.lower() for x in [
                    "gene", "dna", "genome", "genetic",
                    "biology", "biotech", "crispr"
                ]):
                    print("⛔ skipping non-genetics narration")
                    continue

                if any(ord(x) > 127 for x in safe):
                    continue

                try:
                    print("🔊 TTS:", safe[:80])
                    narration_paths.append(generate_audio(safe[:500]))
                except:
                    continue

        except Exception as e:
            print("⚠️ AI error:", e)

    # ---------- STITCH ----------
    final_audio = None

    sequence = narration_paths + clip_paths if narration_paths else clip_paths

    if sequence:
        try:
            fn = stitch_blendz(sequence, target_minutes)
            final_audio = f"/audio/final/{fn}"
        except Exception as e:
            print("🔥 stitch error:", e)

    return {
        "query": query,
        "results": blended,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
    }


# ---------------- ENDPOINT ----------------
@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board = BOARD_CONFIG.get(board_id)

    if not board:
        return {"error": "Board not found"}

    return {
        "mode": "board",
        **run_blend(
            board["query"],
            minutes or board["default_minutes"],
            True,
        ),
    }




