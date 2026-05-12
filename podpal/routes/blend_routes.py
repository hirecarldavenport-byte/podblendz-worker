from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed
from podpal.blending.round_robin import round_robin_blend

# ✅ AI pipeline
from podpal.ai.pipeline import process_clusters

# ✅ Audio ingestion
from podpal.audio.ingest import download_episode_audio


router = APIRouter()


# -------------------------------------------------
# ✅ Utility: Clean HTML
# -------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""

    # ✅ FIX: correct HTML stripping
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# -------------------------------------------------
# ✅ BLEND ENDPOINT
# -------------------------------------------------
@router.post("/blend")
def preview_blend(
    query: Optional[str] = Body(default=None),
    podcaster_feed: Optional[str] = Body(default=None),
    enable_ai: bool = Body(default=True),
) -> Dict[str, Any]:

    # =================================================
    # PODCASTER MODE
    # =================================================
    if podcaster_feed:
        from podpal.retrieval.podcasters import fetch_podcaster_episodes

        episodes = fetch_podcaster_episodes(podcaster_feed)

        if not episodes:
            return {
                "mode": "podcaster",
                "guidance": "No recent episodes with transcripts.",
                "results": [],
            }

        return {
            "mode": "podcaster",
            "episode_count": len(episodes),
            "results": episodes,
        }

    # =================================================
    # SUBJECT MODE
    # =================================================
    if not query:
        return {
            "mode": "subject",
            "guidance": "Provide a query or podcaster_feed.",
            "results": [],
        }

    print(f"\n🔍 [SEARCH] Incoming query: '{query}'")

    # -------------------------------------------------
    # 1. Resolve feeds
    # -------------------------------------------------
    feed_urls = resolve_search_term(query)

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except Exception as e:
            print(f"⚠️ Feed resolution failed: {e}")

    if not feeds:
        return {
            "mode": "subject",
            "query": query,
            "guidance": "No podcasts resolved.",
            "results": [],
        }

    feeds = feeds[:25]

    # -------------------------------------------------
    # 2. Fetch episodes
    # -------------------------------------------------
    episodes_by_feed: Dict[str, List[Any]] = {}

    for feed in feeds:
        try:
            rss = fetch_rss_feed(feed.feed_url)
            episodes_by_feed[feed.feed_url] = rss.get("items", []) if rss else []
        except Exception as e:
            print(f"⚠️ RSS issue: {e}")
            episodes_by_feed[feed.feed_url] = []

    if not episodes_by_feed:
        return {
            "mode": "subject",
            "query": query,
            "results": [],
        }

    # -------------------------------------------------
    # 3. Blend episodes
    # -------------------------------------------------
    blended_episodes = round_robin_blend(
        episodes_by_podcaster=episodes_by_feed,
        max_per_podcaster=1,
        max_total=3,
    )

    # -------------------------------------------------
    # 4. Download audio (resilient)
    # -------------------------------------------------
    clip_paths = []

    for ep in blended_episodes:
        try:
            audio_url = None

            for link in ep.get("links", []):
                if link.get("type") == "audio/mpeg":
                    audio_url = link.get("href")
                    break

            if not audio_url:
                ep["local_audio"] = None
                continue

            filename = download_episode_audio(audio_url)

            if filename:
                local_path = f"/audio/{filename}"
                ep["local_audio"] = local_path

                # ✅ convert to full path for later stitching
                full_path = str(
                    Path(__file__).resolve().parent.parent.parent
                    / "audio"
                    / "raw"
                    / filename
                )
                clip_paths.append(full_path)
            else:
                ep["local_audio"] = None

        except Exception as e:
            print(f"⚠️ Audio ingestion failed: {e}")
            ep["local_audio"] = None

    # -------------------------------------------------
    # 5. AI enrichment
    # -------------------------------------------------
    ai_output = None

    if enable_ai:
        try:
            segments = []

            for ep in blended_episodes:
                raw = (
                    ep.get("transcript")
                    or ep.get("summary")
                    or ep.get("description")
                )

                cleaned = clean_text(raw)

                if cleaned and len(cleaned) > 100:
                    segments.append(cleaned)

            if segments:
                clusters = [
                    {"id": i + 1, "segments": [seg]}
                    for i, seg in enumerate(segments[:3])
                ]

                print("\n🧠 --- CLUSTERS ---")
                print(clusters)

                ai_output = process_clusters(clusters)

                print("\n🧠 --- AI OUTPUT ---")
                print(ai_output)

        except Exception as e:
            print(f"⚠️ AI error: {e}")

    # -------------------------------------------------
    # 6. RESPONSE (no audio yet guaranteed)
    # -------------------------------------------------
    return {
        "mode": "subject",
        "query": query,
        "results": blended_episodes,
        "ai": ai_output,
        "clip_count": len(clip_paths),  # ✅ useful debug
    }

