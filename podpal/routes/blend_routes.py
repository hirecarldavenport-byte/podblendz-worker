from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

# ✅ Core modules
from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed
from podpal.blending.round_robin import round_robin_blend

# ✅ AI
from podpal.ai.pipeline import process_clusters

# ✅ Audio
from podpal.audio.ingest import download_episode_audio
from podpal.audio.tts import generate_audio
from podpal.audio.stitch import stitch_blendz

# ✅ Boards
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

    for sentence in sentences:
        if len(current) + len(sentence) < max_len:
            current += sentence + ". "
        else:
            chunks.append(current.strip())
            current = sentence + ". "

    if current:
        chunks.append(current.strip())

    return chunks


# -------------------------------------------------
# ✅ RELEVANCE FILTER
# -------------------------------------------------
def is_relevant_episode(ep: Dict[str, Any], query: str) -> bool:
    text = (
        ep.get("title", "") + " " +
        ep.get("summary", "") + " " +
        ep.get("description", "")
    ).lower()

    query_lower = query.lower()

    if query_lower in text:
        return True

    query_terms = query_lower.split()
    matches = sum(1 for word in query_terms if word in text)

    if len(query_terms) <= 2:
        return matches == len(query_terms)

    return matches >= 2


# -------------------------------------------------
# ✅ DOMAIN FILTER
# -------------------------------------------------
def enforce_domain_filter(ep: Dict[str, Any], query: str) -> bool:
    text = (
        ep.get("title", "") + " " +
        ep.get("summary", "") + " " +
        ep.get("description", "")
    ).lower()

    query_lower = query.lower()

    if "genetics" in query_lower or "biology" in query_lower:
        return any(term in text for term in [
            "dna", "gene", "genetic", "biology", "cells"
        ])

    if "ai" in query_lower:
        return any(term in text for term in [
            "ai", "machine learning", "model", "algorithm"
        ])

    return True


# -------------------------------------------------
# ✅ LOW QUALITY FILTER
# -------------------------------------------------
def exclude_low_quality(ep: Dict[str, Any]) -> bool:
    text = (
        ep.get("title", "") + " " +
        ep.get("summary", "") + " " +
        ep.get("description", "")
    ).lower()

    bad_signals = [
        "weekly podcast",
        "we talk about",
        "random topics",
        "two friends",
        "variety podcast",
        "new episode every",
    ]

    return not any(bad in text for bad in bad_signals)


# -------------------------------------------------
# ✅ MAIN BLEND LOGIC (REUSABLE CORE)
# -------------------------------------------------
def run_blend(query: str, target_minutes: int, enable_ai: bool):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n🔍 QUERY: {query}")

    # --------------------
    # SEARCH
    # --------------------
    feed_urls = resolve_search_term(query)

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except Exception:
            continue

    feeds = feeds[:25]

    # --------------------
    # FETCH EPISODES
    # --------------------
    episodes_by_feed: Dict[str, List[Any]] = {}

    for feed in feeds:
        try:
            rss = fetch_rss_feed(feed.feed_url)
            episodes_by_feed[feed.feed_url] = rss.get("items", [])
        except Exception:
            episodes_by_feed[feed.feed_url] = []

    blended = round_robin_blend(
        episodes_by_podcaster=episodes_by_feed,
        max_per_podcaster=1,
        max_total=5,
    )

    # --------------------
    # FILTER
    # --------------------
    filtered = [
        ep for ep in blended
        if is_relevant_episode(ep, query)
        and enforce_domain_filter(ep, query)
        and exclude_low_quality(ep)
    ]

    if filtered:
        blended = filtered
        print(f"✅ Filtered to {len(blended)} episodes")
    else:
        print("⚠️ No strong matches")

    if not blended:
        return {
            "query": query,
            "results": [],
            "final_audio": None,
        }

    # --------------------
    # AUDIO INGEST
    # --------------------
    clip_paths = []

    for ep in blended:
        try:
            audio_url = None

            for link in ep.get("links", []):
                if "audio" in link.get("type", ""):
                    audio_url = link.get("href")
                    break

            if not audio_url:
                continue

            filename = download_episode_audio(audio_url)

            if filename:
                clip_paths.append(str(RAW_DIR / filename))

        except Exception:
            continue

    print("🎧 clip_paths:", clip_paths)

    # --------------------
    # AI + TTS
    # --------------------
    narration_paths = []
    ai_output = None

    if enable_ai:
        try:
            segments = []

            for ep in blended:
                raw = ep.get("summary") or ep.get("description")
                cleaned = clean_text(raw)

                if cleaned:
                    chunks = split_into_chunks(cleaned)
                    segments.extend(chunks[:2])

            if segments:
                clusters = [
                    {"id": i + 1, "segments": [seg]}
                    for i, seg in enumerate(segments[:5])
                ]

                ai_output = process_clusters(clusters)

                for cluster in ai_output:
                    narration = cluster.get("narration")
                    if narration:
                        narration_paths.append(generate_audio(narration))

        except Exception as e:
            print("⚠️ AI error:", e)

    # --------------------
    # STITCH
    # --------------------
    final_audio = None

    try:
        sequence = []

        for i in range(len(narration_paths)):
            sequence.append(narration_paths[i])

            if i < len(clip_paths):
                sequence.append(clip_paths[i])

        if sequence:
            filename = stitch_blendz(sequence, target_minutes=target_minutes)
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


# -------------------------------------------------
# ✅ BLEND ENDPOINT
# -------------------------------------------------
@router.post("/blend")
def preview_blend(
    query: Optional[str] = Body(default=None),
    enable_ai: bool = Body(default=True),
    target_minutes: int = Body(default=5),
):
    if not query:
        return {"error": "Query required"}

    result = run_blend(query, target_minutes, enable_ai)

    return {
        "mode": "subject",
        **result
    }


# -------------------------------------------------
# ✅ BOARD ENDPOINT (NEW 🎯)
# -------------------------------------------------
@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board = BOARD_CONFIG.get(board_id)

    if not board:
        return {
            "error": "Board not found",
            "available_boards": list(BOARD_CONFIG.keys())
        }

    query = board["query"]
    target_minutes = minutes or board["default_minutes"]

    print(f"\n📌 BOARD: {board_id}")

    result = run_blend(query, target_minutes, True)

    return {
        "mode": "board",
        "board_id": board_id,
        "title": board["title"],
        **result
    }


