"""
WEEKLY INGEST (CLEAN DEBUG VERSION)

✅ Confirms correct file execution
✅ Ensures transcription runs
✅ No silent failures
"""

# =========================
# DEBUG MARKER (CRITICAL)
# =========================
print("##### UPDATED WEEKLY INGEST RUNNING #####")

import sys
import os
from pathlib import Path
from datetime import datetime

import feedparser

# ✅ Confirm exact file being executed
print("RUNNING FILE:", os.path.abspath(__file__))

# =========================
# FIX IMPORT PATH
# =========================
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

# =========================
# IMPORTS
# =========================
from podpal.topics.master_topic_podcasters import TOP_PODCASTERS_BY_MASTER_TOPIC
from podpal.db.session import get_session
from podpal.db.models import Podcast
from podpal.ingestion.audio import ingest_episode_audio
from podpal.transcription.transcribe import transcribe_audio


# =========================
# SETTINGS
# =========================
MAX_EPISODES = 2   # keep small while debugging


# =========================
# MAIN FUNCTION
# =========================
def run_weekly_ingestion():

    print("\n=== INGEST START ===")
    print("Topics:", list(TOP_PODCASTERS_BY_MASTER_TOPIC.keys()))
    print("Time:", datetime.utcnow().isoformat())

    session = get_session()

    for topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():

        print(f"\n=== TOPIC: {topic} ===")

        for podcaster in podcasters:

            if not podcaster.get("ingestible"):
                continue

            if podcaster.get("media_access") != "direct":
                continue

            feed_url = podcaster.get("feed_url")
            if not feed_url:
                continue

            podcast_id = podcaster["id"]

            podcast = session.query(Podcast).filter_by(id=podcast_id).first()

            if not podcast:
                print("[WARN] Podcast not in DB:", podcast_id)
                continue

            print(f"[INGEST] Fetching: {podcaster['name']}")

            feed = feedparser.parse(feed_url)

            if not feed.entries:
                print("[WARN] No entries found")
                continue

            for item in feed.entries[:MAX_EPISODES]:

                title = item.get("title", "unknown")
                print("\n--- Episode:", title, "---")

                # =========================
                # AUDIO
                # =========================
                try:
                    audio_info = ingest_episode_audio(
                        master_topic=topic,
                        podcast=podcast,
                        rss_item=item,
                    )
                except Exception as e:
                    print("[ERROR] Audio failed:", e)
                    continue

                print(">>> AUDIO BLOCK REACHED")

                if not audio_info:
                    print("[WARN] No audio_info returned")
                    continue

                audio_path = audio_info.get("local_path")
                episode_id = audio_info.get("episode_id")

                if not audio_path or not episode_id:
                    print("[WARN] Missing audio_path or episode_id")
                    continue

                print("[AUDIO] Path:", audio_path)

                # =========================
                # TRANSCRIPTION
                # =========================
                print(">>> TRANSCRIPTION BLOCK REACHED")

                try:
                    print("[TRANSCRIBE] Starting:", episode_id)

                    transcript_path = transcribe_audio(
                        audio_path=audio_path,
                        podcast_id=podcast_id,
                        episode_id=episode_id,
                    )

                    print("[TRANSCRIBE] Saved:", transcript_path)

                except Exception as e:
                    print("[ERROR] Transcription failed:", e)
                    continue

    print("\n=== INGEST COMPLETE ===")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    run_weekly_ingestion()
