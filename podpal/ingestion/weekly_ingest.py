"""
Weekly Ingestion Pipeline

✅ Safe ingestion loop
✅ Handles missing audio gracefully
✅ Uses local storage (no AWS)
✅ Production-safe iteration
"""

import sys
from pathlib import Path
from datetime import datetime, UTC
import feedparser

# ✅ Fix module path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from podpal.topics.master_topic_podcasters import (
    TOP_PODCASTERS_BY_MASTER_TOPIC,
)
from podpal.db.session import get_session
from podpal.db.models import Podcast
from podpal.ingestion.audio import ingest_episode_audio


# =========================
# CORE INGESTION
# =========================

def run_weekly_ingestion():

    print("[SANITY] run_weekly_ingestion() entered")
    print(f"[SANITY] registry keys: {list(TOP_PODCASTERS_BY_MASTER_TOPIC.keys())}")

    session = get_session()

    print(f"[INGEST] Weekly ingestion started at {datetime.now(UTC).isoformat()}")

    for master_topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():
        print(f"[INGEST] Topic: {master_topic}")

        for podcaster in podcasters:

            if not podcaster.get("ingestible"):
                continue

            if podcaster.get("media_access") != "direct":
                continue

            feed_url = podcaster.get("feed_url")

            if not feed_url:
                continue

            podcast_id = podcaster["id"]

            podcast_obj = session.query(Podcast).filter_by(id=podcast_id).first()

            if not podcast_obj:
                print(f"[WARN] Podcast id='{podcast_id}' not found in DB. Skipping.")
                continue

            print(f"[INGEST] Fetching RSS for {podcaster['name']}")

            feed = feedparser.parse(feed_url)

            if not feed.entries:
                print(f"[WARN] No entries found for {podcaster['name']}")
                continue

            print(f"[INGEST] {len(feed.entries)} total episode(s) found")

            # ✅ LIMIT FOR DEV (important for now)
            max_episodes = 3

            for item in feed.entries[:max_episodes]:

                title = item.get("title", "unknown")

                print(f"[INGEST] Processing episode: {title}")

                # =========================
                # AUDIO INGESTION
                # =========================

                audio_info = ingest_episode_audio(
                    master_topic=master_topic,
                    podcast=podcast_obj,
                    rss_item=item,
                )

                # ✅ CRITICAL FIX (prevents crash)
                if not audio_info:
                    print(f"[WARN] Skipping episode (no audio): {title}")
                    continue

                # ✅ New structure (dict-based)
                audio_path = audio_info.get("local_path")

                if not audio_path:
                    print(f"[WARN] No local audio path found. Skipping.")
                    continue

                print(f"[INGEST] Audio stored at: {audio_path}")

                # =========================
                # PLACEHOLDER FOR NEXT STEP
                # =========================

                # Later:
                # - save episode record
                # - trigger transcription
                # - attach metadata

    print("[INGEST] Weekly ingestion completed successfully.")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_weekly_ingestion()
