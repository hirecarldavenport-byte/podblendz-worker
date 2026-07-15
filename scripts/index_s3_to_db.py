import sqlite3
import boto3
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "podblendz.db"

S3_BUCKET = "podblendz-episode-audio"
BASE_PREFIX = "raw_audio"
MASTER_TOPIC = "media_culture"

PODCAST_IDS = [
    "kevonstage_not_my_best_moment"
]

AUDIO_EXTENSION = ".mp3"

# ============================================================
# SETUP
# ============================================================

s3 = boto3.client("s3")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# ============================================================
# HELPERS
# ============================================================

def episode_exists(episode_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM episodes WHERE id = ?",
        (episode_id,)
    ).fetchone() is not None


def insert_episode(episode_id: str, podcast_id: str, s3_key: str):
    """
    Insert a new episode row.

    NOTE:
    - guid is required (NOT NULL), so we safely reuse episode_id
    - published_at is intentionally left NULL (can be backfilled later)
    """
    conn.execute(
        """
        INSERT INTO episodes (
            id,
            guid,
            podcast_id,
            audio_s3_key,
            storage_tier,
            transcript_status,
            ingested_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            episode_id,   # id
            episode_id,   # guid (safe stand-in)
            podcast_id,
            s3_key,
            "s3",
            "pending",
        )
    )


# ============================================================
# INDEXING LOGIC
# ============================================================

def index_podcast(podcast_id: str):
    prefix = f"{BASE_PREFIX}/{MASTER_TOPIC}/{podcast_id}/"
    print(f"\n🔍 Scanning s3://{S3_BUCKET}/{prefix}")

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=S3_BUCKET,
        Prefix=prefix,
    )

    inserted = 0
    skipped = 0

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]

            # Ignore non-audio files
            if not key.lower().endswith(AUDIO_EXTENSION):
                continue

            episode_id = Path(key).stem

            if episode_exists(episode_id):
                skipped += 1
                continue

            insert_episode(
                episode_id=episode_id,
                podcast_id=podcast_id,
                s3_key=key,
            )
            inserted += 1

    conn.commit()
    print(f"✅ {podcast_id}: inserted={inserted}, skipped={skipped}")


def main():
    print("🚀 Starting S3 → DB indexing (audio catalog backfill)")

    for podcast_id in PODCAST_IDS:
        index_podcast(podcast_id)

    conn.close()
    print("\n✅ Indexing complete — S3 and DB are now aligned")


if __name__ == "__main__":
    main()
