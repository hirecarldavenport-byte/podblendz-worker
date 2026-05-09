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
import sys
from pathlib import Path

# ✅ FORCE ROOT PATH (this fixes everything)
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime
from typing import Optional, Dict, List

from podpal.topics.master_topic_podcasters import TOP_PODCASTERS_BY_MASTER_TOPIC
from podpal.ingestion.rss import fetch_rss_items
from podpal.ingestion.audio import ingest_episode_audio
from podpal.ingestion.retention import enforce_retention

from podpal.db.session import get_session
from podpal.db.models import Podcast, Episode

MAX_EPISODES_PER_PODCAST = 50


def run_weekly_ingestion(dry_run: bool = False) -> None:
    # -------------------------------------------------
    # SANITY CHECKS
    # -------------------------------------------------
    print("[SANITY] run_weekly_ingestion() entered")
    print(
        "[SANITY] registry keys:",
        list(TOP_PODCASTERS_BY_MASTER_TOPIC.keys()),
    )
    # -------------------------------------------------

    print(
        f"[INGEST] Weekly ingestion started at "
        f"{datetime.utcnow().isoformat()}"
    )

    session = get_session()

    try:
        for master_topic, podcast_configs in (
            TOP_PODCASTERS_BY_MASTER_TOPIC.items()
        ):
            print(f"[INGEST] Topic: {master_topic}")

            for podcast_cfg in podcast_configs:
                podcast_id: Optional[str] = podcast_cfg.get("id")
                if not podcast_id:
                    # Registry entry intentionally non-ingestable
                    continue

                podcast_obj: Optional[Podcast] = (
                    session.query(Podcast)
                    .filter(Podcast.id == podcast_id)
                    .one_or_none()
                )

                if podcast_obj is None:
                    print(
                        f"[WARN] Podcast id='{podcast_id}' "
                        f"not found in DB. Skipping."
                    )
                    continue

                # --- feed_url must be coerced to a concrete string ---
                raw_feed_url = podcast_obj.feed_url
                feed_url: str = (
                    str(raw_feed_url).strip()
                    if raw_feed_url is not None
                    else ""
                )

                if not feed_url:
                    print(
                        f"[WARN] Podcast '{podcast_obj.name}' "
                        f"has no feed URL. Skipping."
                    )
                    continue

                print(f"[INGEST] Fetching RSS for {podcast_obj.name}")

                rss_items = fetch_rss_items(feed_url)
                if not rss_items:
                    print(
                        f"[INGEST] No RSS items for "
                        f"{podcast_obj.name}"
                    )
                    continue

                # --- gather already-ingested GUIDs ---
                existing_guids = {
                    guid
                    for (guid,) in (
                        session.query(Episode.guid)
                        .filter(
                            Episode.podcast_id == podcast_obj.id
                        )
                        .all()
                    )
                }

                new_items = [
                    item
                    for item in rss_items
                    if item.guid not in existing_guids
                ]

                if not new_items:
                    print(
                        f"[INGEST] No new episodes for "
                        f"{podcast_obj.name}"
                    )
                    continue

                print(
                    f"[INGEST] {len(new_items)} new episode(s) "
                    f"found for {podcast_obj.name}"
                )

                for item in new_items:
                    print(
                        f"[INGEST] Processing episode: "
                        f"{item.title}"
                    )

                    if dry_run:
                        print(
                            "[DRY-RUN] Skipping audio ingest "
                            "and DB insert."
                        )
                        continue

                    audio_info = ingest_episode_audio(
                        master_topic=master_topic,
                        podcast=podcast_obj,
                        rss_item=item,
                    )

                    episode = Episode(
                        id=str(item.guid),
                        podcast_id=podcast_obj.id,
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

                    print(
                        f"[INGEST] Episode committed: "
                        f"{episode.title}"
                    )

                # --- retention requires a concrete string id ---
                podcast_id_str = str(podcast_obj.id)

                print(
                    f"[INGEST] Enforcing retention for "
                    f"{podcast_obj.name}"
                )

                enforce_retention(
                    session=session,
                    podcast_id=podcast_id_str,
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