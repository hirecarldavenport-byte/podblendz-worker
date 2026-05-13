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
# ✅ STRONG RELEVANCE FILTER
# -------------------------------------------------
def is_relevant_episode(ep: Dict[str, Any], query: str) -> bool:
    text = (ep.get("title", "") + " " +
            ep.get("summary", "") + " " +
            ep.get("description", "")).lower()

    query_lower = query.lower()

    if query_lower in text:
        return True

    query_terms = query_lower.split()
    matches = sum(1 for word in query_terms if word in text)

    if len(query_terms) <= 2:
        return matches == len(query_terms)

    if matches < max(2, len(query_terms) // 2):
        return False

    # ✅ block "Gene Quinn" issue
    if "gene " in text and not any(x in text for x in ["dna", "genetic", "crispr"]):
        return False

    return True


# -------------------------------------------------
# ✅ DOMAIN FILTER (SCORING)
# -------------------------------------------------
def enforce_domain_filter(ep: Dict[str, Any], query: str) -> bool:
    text = (ep.get("title", "") + " " +
            ep.get("summary", "") + " " +
            ep.get("description", "")).lower()

    query_lower = query.lower()

    if any(x in query_lower for x in ["genetics", "crispr", "gene", "biotech"]):

        strong = [
            "dna", "gene editing", "genetic", "crispr",
            "genome", "cell", "molecular",
            "protein", "rna", "antibody"
        ]

        weak = ["research", "lab", "biology", "science"]

        score = sum(2 for x in strong if x in text)
        score += sum(1 for x in weak if x in text)

        return score >= 3

    if "ai" in query_lower:
        terms = ["ai", "machine learning", "model", "algorithm"]
        return sum(1 for t in terms if t in text) >= 2

    return True


# -------------------------------------------------
# ✅ LOW QUALITY FILTER
# -------------------------------------------------
def exclude_low_quality(ep: Dict[str, Any]) -> bool:
    text = (ep.get("title", "") + " " +
            ep.get("summary", "") + " " +
            ep.get("description", "")).lower()

    bad_phrases = [
        "weekly podcast",
        "we talk about",
        "random topics",
        "two friends",
        "variety podcast",
    ]

    bad_domains = [
        "torah", "idol worship",
        "politics", "trump",
        "economics", "basketball", "sports"
    ]

    if any(b in text for b in bad_phrases):
        return False

    if any(b in text for b in bad_domains):
        return False

    if len(text.split()) < 25:
        return False

    return True


# -------------------------------------------------
# ✅ CORE BLEND FUNCTION
# -------------------------------------------------
def run_blend(query: str, target_minutes: int, enable_ai: bool):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n🔍 QUERY: {query}")

    feed_urls = resolve_search_term(query)

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except:
            continue

    feeds = feeds[:25]

    episodes_by_feed = {}

    for feed in feeds:
        try:
            rss = fetch_rss_feed(feed.feed_url)
            episodes_by_feed[feed.feed_url] = rss.get("items", [])
        except:
            episodes_by_feed[feed.feed_url] = []

    blended = round_robin_blend(
        episodes_by_podcaster=episodes_by_feed,
        max_per_podcaster=1,
        max_total=5,
    )

    filtered = [
        ep for ep in blended
        if is_relevant_episode(ep, query)
        and enforce_domain_filter(ep, query)
        and exclude_low_quality(ep)
    ]

    if filtered:
        blended = filtered[:3]
        print(f"✅ Filtered to {len(blended)} episodes")
    else:
        print("⚠️ No relevant content → stopping")
        return {
            "query": query,
            "results": [],
            "ai": None,
            "clip_count": 0,
            "final_audio": None,
        }

    # AUDIO INGEST
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
        except:
            continue

    print("🎧 clip_paths:", clip_paths)

    narration_paths = []
    ai_output = None

    if enable_ai:
        try:
            segments = []
            for ep in blended:
                raw = ep.get("summary") or ep.get("description")
                cleaned = clean_text(raw)

                if cleaned:
                    segments.extend(split_into_chunks(cleaned)[:2])

            if segments:
                clusters = [{"id": i + 1, "segments": [seg]} for i, seg in enumerate(segments[:5])]
                ai_output = process_clusters(clusters)

                for cluster in ai_output:
                    narration = cluster.get("narration")

                    # ✅ SAFE NARRATION HANDLING
                    if not narration:
                        continue

                    safe = narration.strip()

                    if len(safe) < 50:
                        continue

                    if "please provide" in safe.lower():
                        continue

                    try:
                        path = generate_audio(safe[:3000])
                        narration_paths.append(path)
                    except Exception as e:
                        print("⚠️ Skipping narration:", e)

        except Exception as e:
            print("⚠️ AI error:", e)

    final_audio = None

    if narration_paths:
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
# ✅ BLEND
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

    return {"mode": "subject", **result}


# -------------------------------------------------
# ✅ BOARD
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




