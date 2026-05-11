from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
import re

from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed

from podpal.blending.round_robin import round_robin_blend

# ✅ AI pipeline
from podpal.ai.pipeline import process_clusters


router = APIRouter()


# -------------------------------------------------
# ✅ Utility: Clean HTML from RSS content
# -------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""

    # remove HTML tags
    text = re.sub(r"<.*?>", "", text)

    # collapse whitespace
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
    """
    Generate:
    - SUBJECT blend (search-based)
    - PODCASTER blend (direct)

    Includes optional AI narration.
    """

    # =================================================
    # PODCASTER MODE (UNCHANGED)
    # =================================================
    if podcaster_feed:
        from podpal.retrieval.podcasters import fetch_podcaster_episodes

        episodes = fetch_podcaster_episodes(podcaster_feed)

        if not episodes:
            return {
                "mode": "podcaster",
                "podcaster_feed": podcaster_feed,
                "guidance": (
                    "No recent episodes with transcripts were available "
                    "for this podcaster."
                ),
                "results": [],
            }

        return {
            "mode": "podcaster",
            "podcaster_feed": podcaster_feed,
            "vibe": {
                "type": "creator",
                "description": (
                    "Latest episodes from this creator, "
                    "presented in order of release."
                ),
            },
            "episode_count": len(episodes),
            "results": episodes,
        }

    # =================================================
    # SUBJECT MODE
    # =================================================
    if not query:
        return {
            "mode": "subject",
            "guidance": (
                "Provide either a query (subject blend) "
                "or a podcaster_feed (creator mode)."
            ),
            "results": [],
        }

    # -------------------------------------------------
    # 1. Resolve query → feeds
    # -------------------------------------------------
    feed_urls = resolve_search_term(query)

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except Exception as e:
            print(f"⚠️ Feed resolution failed for {url}: {e}")

    if not feeds:
        return {
            "mode": "subject",
            "query": query,
            "guidance": "No podcasts could be resolved for this topic.",
            "results": [],
        }

    feeds = feeds[:25]

    # -------------------------------------------------
    # 2. Fetch episodes
    # -------------------------------------------------
    episodes_by_feed: Dict[str, List[Any]] = {}

    for feed in feeds:
        feed_url = feed.feed_url
        try:
            rss_data = fetch_rss_feed(feed_url)
            episodes_by_feed[feed_url] = (
                rss_data.get("items", []) if rss_data else []
            )
        except Exception as e:
            print(f"⚠️ RSS feed issue for {feed_url}: {e}")
            episodes_by_feed[feed_url] = []

    if not episodes_by_feed:
        return {
            "mode": "subject",
            "query": query,
            "guidance": "No usable episodes were found.",
            "results": [],
        }

    # -------------------------------------------------
    # 3. Round robin blend
    # -------------------------------------------------
    blended_episodes = round_robin_blend(
        episodes_by_podcaster=episodes_by_feed,
        max_per_podcaster=1,
        max_total=3,
    )

    # -------------------------------------------------
    # ✅ 4. AI ENRICHMENT (IMPROVED)
    # -------------------------------------------------
    ai_output = None

    if enable_ai:
        try:
            segments = []

            for ep in blended_episodes:
                raw_text = (
                    ep.get("transcript")
                    or ep.get("summary")
                    or ep.get("description")
                )

                cleaned = clean_text(raw_text)

                # ✅ Skip junk / too short
                if cleaned and len(cleaned) > 100:
                    segments.append(cleaned)

            # ✅ Multi-cluster instead of one blob
            if segments:
                clusters = []

                for i, segment in enumerate(segments[:3]):  # limit clusters
                    clusters.append({
                        "id": i + 1,
                        "segments": [segment]
                    })

                print("\n--- CLUSTERS ---")
                print(clusters)

                ai_output = process_clusters(clusters)

                print("\n--- AI OUTPUT ---")
                print(ai_output)

        except Exception as e:
            print(f"⚠️ AI processing failed: {e}")

    # -------------------------------------------------
    # 5. Response
    # -------------------------------------------------
    return {
        "mode": "subject",
        "query": query,
        "guidance": "Showing the latest relevant episode from each creator.",
        "results": blended_episodes,
        "ai": ai_output,
    }
