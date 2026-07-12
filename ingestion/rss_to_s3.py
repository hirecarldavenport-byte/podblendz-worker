"""
rss_to_s3.py

Stable RSS → S3 ingestion
Stores episode title metadata for downstream PodBlendz card generation.
"""

from pathlib import Path
from typing import Optional
import argparse
import hashlib
import json

import boto3
import feedparser
import requests

from podpal.topics.master_topic_podcasters import iter_ingestible_podcasters


# =================================================
# CONFIG
# =================================================

AWS_REGION = "us-east-1"
S3_BUCKET = "podblendz-episode-audio"
S3_PREFIX = "raw_audio"

REQUEST_TIMEOUT = 30
MAX_AUDIO_MB = 500

EPISODE_METADATA_BASE = Path("ingestion/episode_metadata")
EPISODE_METADATA_BASE.mkdir(parents=True, exist_ok=True)


# =================================================
# AWS CLIENT
# =================================================

s3 = boto3.client("s3", region_name=AWS_REGION)


# =================================================
# HELPERS
# =================================================

def compute_episode_id(podcaster_id: str, audio_url: str) -> str:
    h = hashlib.sha256(
        f"{podcaster_id}:{audio_url}".encode("utf-8")
    )
    return h.hexdigest()[:32]


def already_ingested(s3_key: str) -> bool:
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except Exception:
        return False


def extract_audio_url(entry):
    
    enclosures = entry.get("enclosures")

    if not enclosures:
        return None

    first = enclosures[0]

    if isinstance(first, dict):
        return first.get("url")

    return None


def extract_episode_title(entry) -> str:
    title = entry.get("title", "")
    title = str(title).strip()

    if not title:
        return "Untitled Episode"

    return title


def download_audio(url):
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )
        response.raise_for_status()

        total = 0
        chunks = []

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if not chunk:
                continue

            total += len(chunk)

            if total > MAX_AUDIO_MB * 1024 * 1024:
                print(
                    f"⚠️ Skipping large file (> {MAX_AUDIO_MB} MB)"
                )
                return None

            chunks.append(chunk)

        return b"".join(chunks)

    except Exception as exc:
        print(f"⚠️ Download failed: {exc}")
        return None


# =================================================
# INGESTION
# =================================================

def ingest_feed(
    master_topic: str,
    podcaster_id: str,
    feed_url: str,
    *,
    dry_run: bool,
):
    try:
        feed = feedparser.parse(feed_url)
    except Exception as exc:
        print(f"❌ Feed parse failed: {exc}")
        return

    if not feed.entries:
        print(f"⚠️ No entries for {podcaster_id}")
        return

    for entry in feed.entries:
        audio_url = extract_audio_url(entry)

        if not audio_url:
            continue

        episode_title = extract_episode_title(entry)

        audio_url = str(audio_url)

        episode_id = compute_episode_id(
            podcaster_id=podcaster_id,
            audio_url=audio_url,
        )

        s3_key = (
            f"{S3_PREFIX}/"
            f"{master_topic}/"
            f"{podcaster_id}/"
            f"{episode_id}.mp3"
        )

        if not already_ingested(s3_key):
            audio_bytes = download_audio(audio_url)

            if audio_bytes is None:
                continue

            if dry_run:
                print(f"[DRY] Upload → {s3_key}")
            else:
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=audio_bytes,
                    ContentType="audio/mpeg",
                    Metadata={
                        "episode_id": episode_id,
                        "podcaster_id": podcaster_id,
                        "title": episode_title[:250],
                    },
                )

        metadata_dir = (
            EPISODE_METADATA_BASE
            / master_topic
            / podcaster_id
        )
        metadata_dir.mkdir(parents=True, exist_ok=True)

        metadata_payload = {
            "episode_id": episode_id,
            "podcaster_id": podcaster_id,
            "master_topic": master_topic,
            "title": episode_title,
            "published": entry.get("published"),
            "audio_url": audio_url,
            "s3_key": s3_key,
        }

        metadata_path = metadata_dir / f"{episode_id}.json"

        if dry_run:
            print(f"[DRY] Metadata → {metadata_path}")
        else:
            with open(
                metadata_path,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    metadata_payload,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        print(
            f"✅ Ingested {podcaster_id}/{episode_id} "
            f"| {episode_title}"
        )


# =================================================
# MAIN
# =================================================

def run(dry_run: bool = False):
    print("▶ Starting ingestion")

    for master_topic, podcaster in iter_ingestible_podcasters():
        feed_url = podcaster.get("feed_url")
        media_access = podcaster.get("media_access")

        if media_access != "direct":
            print(
                f"⚠️ Skipping {podcaster['id']} (blocked)"
            )
            continue

        if not feed_url:
            continue

        try:
            ingest_feed(
                master_topic=master_topic,
                podcaster_id=podcaster["id"],
                feed_url=feed_url,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(
                f"❌ Failed {podcaster['id']}: {exc}"
            )

    print("✔ Done")


# =================================================
# ENTRY
# =================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run)



