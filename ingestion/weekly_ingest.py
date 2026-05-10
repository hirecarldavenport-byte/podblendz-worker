# 🔥 CONFIRM THIS IS CORRECT FILE# 🔥 CONFIRM THIS IS🔥 FULL PIPELINE VERSION FIXED 🔥")

import sys
from pathlib import Path
import feedparser

# =========================
# FIX PATH
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
from podpal.ingestion.feed_utils import fetch_feed
from podpal.transcription.transcribe import transcribe_audio
from podpal.processing.chunk_and_tag import process_transcript

# =========================
# SETTINGS
# =========================
MAX_EPISODES = 2


# =========================
# MAIN
# =========================
def run_ingest():

    print("\n=== STARTING FULL PIPELINE ===")

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
                print("[WARN] Missing podcast:", podcast_id)
                continue

            print(f"[INGEST] {podcaster['name']}")

            # ✅ FIXED FEED FETCH
            feed = fetch_feed(feed_url)

            if not feed or not feed.entries:
                print(f"[WARN] No entries for {podcaster['name']}")
                continue

            for item in feed.entries[:MAX_EPISODES]:

                title = item.get("title", "unknown")
                print("\n--- Episode:", title)

                # =========================
                # AUDIO
                # =========================
                audio_info = ingest_episode_audio(
                    master_topic=topic,
                    podcast=podcast,
                    rss_item=item,
                )

                if not audio_info:
                    continue

                audio_path = audio_info.get("local_path")
                episode_id = audio_info.get("episode_id")

                if not audio_path or not episode_id:
                    continue

                print("[AUDIO]", audio_path)

                # =========================
                # TRANSCRIPTION
                # =========================
                try:
                    transcript_path = transcribe_audio(
                        audio_path=audio_path,
                        podcast_id=podcast_id,
                        episode_id=episode_id,
                    )

                    print("[TRANSCRIPT]", transcript_path)

                except Exception as e:
                    print("[ERROR] Transcribe failed:", e)
                    continue

                # =========================
                # CHUNKING
                # =========================
                try:
                    chunk_path = process_transcript(transcript_path)

                    print("[CHUNK]", chunk_path)

                except Exception as e:
                    print("[ERROR] Chunking failed:", e)
                    continue


# =========================
# RUN
# =========================
if __name__ == "__main__":
    run_ingest()

