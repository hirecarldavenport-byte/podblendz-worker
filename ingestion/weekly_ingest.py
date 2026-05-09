"""
Weekly Ingestion Pipeline

✅ Stable ingestion
✅ Local audio storage
✅ Guaranteed transcription execution
✅ Full debug visibility
✅ Safe against missing data
"""
print("***** NEW WEEKLY INGEST VERSION RUNNING *****")
import sys
from pathlib import Path
from datetime import datetime, UTC

import feedparser

# =========================
# PATH FIX
# =========================

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

# =========================
# IMPORTS
# =========================

from podpal.topics.master_topic_podcasters import (
    TOP_PODCASTERS_BY_MASTER_TOPIC,
)
from podpal.db.session import get_session
from podpal.db.models import Podcast
from podpal.ingestion.audio import ingest_episode_audio
from podpal.transcription.transcribe import transcribe_audio


# =========================
# SETTINGS
# =========================

MAX_EPISODES_PER_RUN = 3


# =========================
# CORE FUNCTION
# =========================

def run_weekly_ingestion():

    print("\n=== WEEKLY INGEST START ===")
    print(f"[INFO] Topics: {list(TOP_PODCASTERS_BY_MASTER_TOPIC.keys())}")
    print(f"[INFO] Start Time: {datetime.now(UTC).isoformat()}")

    session = get_session()

    for master_topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():

        print(f"\n=== TOPIC: {master_topic} ===")

        for podcaster in podcasters:

            # -----------------------------
            # FILTER
            # -----------------------------
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
                print(f"[WARN] Podcast '{podcast_id}' not in DB — skipping")
                continue

            # -----------------------------
            # FETCH RSS
            # -----------------------------
            print(f"[INGEST] Fetching RSS: {podcaster['name']}")

            feed = feedparser.parse(feed_url)

            if not feed.entries:
                print(f"[WARN] No entries found for {podcaster['name']}")
                continue

            print(f"[INFO] {len(feed.entries)} episodes found")

            # -----------------------------
            # PROCESS EPISODES
            # -----------------------------
            for item in feed.entries[:MAX_EPISODES_PER_RUN]:

                title = item.get("title", "unknown")
                print(f"\n--- Processing Episode: {title} ---")

                # -----------------------------
                # AUDIO INGESTION
                # -----------------------------
                try:
                    audio_info = ingest_episode_audio(
                        master_topic=master_topic,
                        podcast=podcast_obj,
                        rss_item=item,
                    )
                except Exception as e:
                    print(f"[ERROR] Audio ingestion failed: {e}")
                    continue

                print("=== AUDIO BLOCK REACHED ===")

                if not audio_info:
                    print("[WARN] No audio_info returned — skipping")
                    continue

                audio_path = audio_info.get("local_path")
                episode_id = audio_info.get("episode_id")

                if not audio_path:
                    print("[WARN] Missing audio_path — skipping")
                    continue

                if not episode_id:
                    print("[WARN] Missing episode_id — skipping")
                    continue

                print(f"[AUDIO] Saved: {audio_path}")

                # -----------------------------
                # TRANSCRIPTION
                # -----------------------------
                print("=== TRANSCRIPTION BLOCK REACHED ===")
                print(f"[TRANSCRIBE] Starting: {episode_id}")

                try:
                    transcript_path = transcribe_audio(
                        audio_path=audio_path,
                        podcast_id=podcast_id,
                        episode_id=episode_id,
                    )

                    print(f"[TRANSCRIBE] Saved: {transcript_path}")

                except Exception as e:
                    print(f"[ERROR] Transcription failed: {e}")
                    continue

    print("\n=== WEEKLY INGEST COMPLETE ===")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_weekly_ingestion()
