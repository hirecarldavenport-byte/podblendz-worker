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
# ✅ SPLIT INTO CHUNKS
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
# ✅ RELEVANCE FILTER (STRONGER VERSION)
# -------------------------------------------------
def is_relevant_episode(ep: Dict[str, Any], query: str) -> bool:
    text = (
        ep.get("title", "") + " " +
        ep.get("summary", "") + " " +
        ep.get("description", "")
    ).lower()

    query_lower = query.lower()

    # ✅ exact phrase match priority
    if query_lower in text:
        return True

    query_terms = query_lower.split()
    matches = sum(1 for word in query_terms if word in text)

    # ✅ stricter logic for short queries
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
            "dna", "gene", "genetic", "biology", "cells", "organism"
        ])

    if "ai" in query_lower:
        return any(term in text for term in [
            "ai", "machine learning", "model", "algorithm", "software"
        ])

    return True


# -------------------------------------------------
# ✅ LOW QUALITY FILTER (VERY IMPORTANT)
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
# ✅ ENDPOINT
# -------------------------------------------------
@router.post("/blend")
def preview_blend(
    query: Optional[str] = Body(default=None),
    podcaster_feed: Optional[str] = Body(default=None),
    enable_ai: bool = Body(default=True),
    target_minutes: int = Body(default=5),  # ✅ NEW
) -> Dict[str, Any]:

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    if podcaster_feed:
        from podpal.retrieval.podcasters import fetch_podcaster_episodes

        episodes = fetch_podcaster_episodes(podcaster_feed)
        return {
            "mode": "podcaster",
            "results": episodes or [],
            "episode_count": len(episodes) if episodes else 0,
        }

    if not query:
        return {
            "mode": "subject",
            "guidance": "Provide a query.",
            "results": [],
        }

    print(f"\n🔍 QUERY: {query}")

    # -------------------------------------------------
    # 1. SEARCH
    # -------------------------------------------------
    feed_urls = resolve_search_term(query)

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except Exception as e:
            print(f"⚠️ Feed fail: {e}")

    feeds = feeds[:25]

    # -------------------------------------------------
    # 2. FETCH
    # -------------------------------------------------
    episodes_by_feed: Dict[str, List[Any]] = {}

    for feed in feeds:
        try:
            rss = fetch_rss_feed(feed.feed_url)
            episodes_by_feed[feed.feed_url] = rss.get("items", []) if rss else []
        except Exception as e:
            print(f"⚠️ RSS fail: {e}")
            episodes_by_feed[feed.feed_url] = []

    # -------------------------------------------------
    # 3. BLEND
    # -------------------------------------------------
    blended_episodes = round_robin_blend(
        episodes_by_podcaster=episodes_by_feed,
        max_per_podcaster=1,
        max_total=5,
    )

    # -------------------------------------------------
    # ✅ FILTER (CORE CONTROL POINT)
    # -------------------------------------------------
    filtered_episodes = [
        ep for ep in blended_episodes
        if is_relevant_episode(ep, query)
        and enforce_domain_filter(ep, query)
        and exclude_low_quality(ep)
    ]

    if filtered_episodes:
        blended_episodes = filtered_episodes
        print(f"✅ Filtered to {len(blended_episodes)} high-quality episodes")
    else:
        print("⚠️ No strong matches → returning no results")

    if len(blended_episodes) < 1:
        return {
            "mode": "subject",
            "query": query,
            "guidance": "No high-quality podcast content found.",
            "results": [],
        }

    # -------------------------------------------------
    # 4. AUDIO INGESTION
    # -------------------------------------------------
    clip_paths: List[str] = []

    for ep in blended_episodes:
        try:
            audio_url = None

            for link in ep.get("links", []):
                if "audio" in link.get("type", ""):  # ✅ FIXED
                    audio_url = link.get("href")
                    break

            if not audio_url:
                ep["local_audio"] = None
                continue

            filename = download_episode_audio(audio_url)

            if filename:
                ep["local_audio"] = f"/audio/{filename}"
                clip_paths.append(str(RAW_DIR / filename))
            else:
                ep["local_audio"] = None

        except Exception as e:
            print(f"⚠️ Download fail: {e}")
            ep["local_audio"] = None

    print("🎧 clip_paths:", clip_paths)

    # -------------------------------------------------
    # 5. AI
    # -------------------------------------------------
    ai_output = None

    if enable_ai:
        try:
            segments = []

            for ep in blended_episodes:
                raw = ep.get("summary") or ep.get("description")
                cleaned = clean_text(raw)

                if cleaned:
                    segments.extend(split_into_chunks(cleaned)[:2])

            if segments:
                clusters = [
                    {"id": i + 1, "segments": [seg]}
                    for i, seg in enumerate(segments[:5])
                ]

                print("\n🧠 CLUSTERS:", clusters)
                ai_output = process_clusters(clusters)

        except Exception as e:
            print(f"⚠️ AI error: {e}")

    # -------------------------------------------------
    # 6. AUDIO PIPELINE
    # -------------------------------------------------
    final_audio = None

    try:
        narration_paths = []
        sequence = []

        if ai_output:
            for cluster in ai_output:
                narration = cluster.get("narration")
                if narration:
                    path = generate_audio(narration)
                    narration_paths.append(path)

        if narration_paths:
            for i in range(len(narration_paths)):
                sequence.append(narration_paths[i])

                if i < len(clip_paths):
                    sequence.append(clip_paths[i])

            final_filename = stitch_blendz(sequence, target_minutes=target_minutes)
            final_audio = f"/audio/final/{final_filename}"

    except Exception as e:
        print(f"🔥 Audio error: {e}")

    return {
        "mode": "subject",
        "query": query,
        "results": blended_episodes,
        "ai": ai_output,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
    }


