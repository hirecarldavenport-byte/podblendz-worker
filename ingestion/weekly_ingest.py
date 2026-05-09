"""
Weekly audio-first ingestion worker for PodBlendz.

Responsibilities:
- Fetch RSS feeds for curated podcasts
- Detect new episodes
- Download and store episode audio in S3
- Insert episode records into the database
- Enforce per-podcast retention limits

This module orchestrates ingestion only.
"""

from datetime import datetime
from typing import Optional

from podpal.topics.master_topic_podcasters import TOP_PODCASTERS_BY_MASTER_TOPIC
from podpal.ingestion.rss import fetch_rss_items
from podpal.ingestion.audio import ingest_episode_audio
from podpal.ingestion.retention import enforce_retention

from podpal.db.session import get_session
from podpal.db.models import Podcast, Episode

MAX_EPISODES_PER_PODCAST = 50


def run_weekly_ingestion(dry_run: bool = False) -> None:
    # -------------------------------------------------
    # SANITY CHECKS (TEMPORARY)
    # -------------------------------------------------
    print("[SANITY] run_weekly_ingestion() entered")
    print("[SANITY] Loaded registry keys:", list(TOP_PODCASTERS_BY_MASTER_TOPIC.keys()))
    # -------------------------------------------------

    print(f"[INGEST] Weekly ingestion started at {datetime.utcnow().isoformat()}")

    session = get_session()

    try:
        for master_topic, podcast_configs in TOP_PODCASTERS_BY_MASTER_TOPIC.items():
            print(f"[INGEST] Topic: {master_topic}")

            for podcast_cfg in podcast_configs:
                podcast_id: Optional[str] = podcast_cfg.get("id")
                if not podcast_id:
                    continue

                podcast_obj = (
                    session.query(Podcast)
                    .filter(Podcast.id == podcast_id)
                    .one_or_none()
                )

                if podcast_obj is None:
                    print(f"[WARN] Podcast {podcast_id} not found in DB. Skipping.")
                    continue

                raw_feed_url = podcast_obj.feed_url
                feed_url_str = str(raw_feed_url) if raw_feed_url is not None else ""

                if not feed_url_str:
                    print(f"[WARN] Podcast {podcast_obj.name} has no feed URL. Skipping.")
                    continue

                print(f"[INGEST] Fetching RSS for {podcast_obj.name}")

                rss_items = fetch_rss_items(feed_url_str)

                if rss_items is None or len(rss_items) == 0:
                    print(f"[INGEST] No RSS items for {podcast_obj.name}")
                    continue

                existing_guids = {
                    e.guid
                    for e in (
                        session.query(Episode.guid)
                        .filter(Episode.podcast_id == str(podcast_obj.id))
                        .all()
                    )
                }

                new_items = [
                    item for item in rss_items
                    if item.guid not in existing_guids
                ]

                if len(new_items) == 0:
                    print(f"[INGEST] No new episodes for {podcast_obj.name}")
                    continue

                print(
                    f"[INGEST] {len(new_items)} new episode(s) found for {podcast_obj.name}"
                )

                for item in new_items:
                    print(f"[INGEST] Processing episode: {item.title}")

                    if dry_run:
                        print("[DRY-RUN] Skipping audio ingest and DB insert.")
                        continue

                    audio_info = ingest_episode_audio(
                        master_topic=master_topic,
                        podcast=podcast_obj,
                        rss_item=item,
                    )

                    episode = Episode(
                        id=str(item.guid),
                        podcast_id=str(podcast_obj.id),
                        guid=str(item.guid),
                        title=item.title,
                        published_at=item.published_at,
                        audio_url=item.enclosure_url,
                        audio_s3_key=audio_info.s3_key,
                        duration_seconds=audio_info.duration_seconds,
                        storage_tier="hot",
                        transcript_status="pending",
                        ingested_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )

                    session.add(episode)
                    session.commit()

                    print(f"[INGEST] Episode committed: {episode.title}")

                print(f"[INGEST] Enforcing retention for {podcast_obj.name}")

                enforce_retention(
                    session=session,
                    podcast_id=str(podcast_obj.id),
                    max_hot_episodes=MAX_EPISODES_PER_PODCAST,
                )

        print("[INGEST] Weekly ingestion completed successfully.")

    except Exception as exc:
        session.rollback()
        print(f"[ERROR] Weekly ingestion failed: {exc}")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    run_weekly_ingestion()