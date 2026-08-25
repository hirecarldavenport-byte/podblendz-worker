import json
import sqlite3
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "podblendz.db"

METADATA_BASE = (
    BASE_DIR
    / "ingestion"
    / "episode_metadata"
)

MASTER_TOPIC = "media_culture"

PODCAST_IDS = [
    "kevonstage_not_my_best_moment",
    "code_switch",
]

# ============================================================
# DB
# ============================================================

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Faster + safer SQLite writes
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")

# ============================================================
# HELPERS
# ============================================================

def episode_exists(guid: str) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM episodes
            WHERE guid = ?
            """,
            (guid,),
        ).fetchone()
        is not None
    )


def insert_episode(metadata: dict):
    """
    Insert episode using the CURRENT schema.

    Existing episodes table columns:

        id
        podcast_id
        guid
        title
        published_at
        audio_url
        audio_s3_key
        duration_seconds
        storage_tier
        transcript_status
        ingested_at
        updated_at
    """

    episode_id = metadata["episode_id"]
    guid = metadata.get("guid") or episode_id

    conn.execute(
        """
        INSERT INTO episodes (
            id,
            podcast_id,
            guid,
            title,
            published_at,
            audio_url,
            audio_s3_key,
            storage_tier,
            transcript_status,
            ingested_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """,
        (
            episode_id,
            metadata["podcaster_id"],
            guid,
            metadata.get("title"),
            metadata.get("published"),
            metadata.get("audio_url"),
            metadata.get("s3_key"),
            "s3",
            "pending",
        ),
    )

# ============================================================
# INDEXING
# ============================================================

def index_podcast(podcast_id: str):

    metadata_dir = (
        METADATA_BASE
        / MASTER_TOPIC
        / podcast_id
    )

    if not metadata_dir.exists():
        print(
            f"⚠️ Missing metadata folder: "
            f"{metadata_dir}"
        )
        return

    inserted = 0
    skipped = 0
    errors = 0

    print(f"\n🔍 Processing {podcast_id}")

    for metadata_file in metadata_dir.glob("*.json"):

        try:

            with open(
                metadata_file,
                "r",
                encoding="utf-8",
            ) as f:
                metadata = json.load(f)

            episode_id = metadata["episode_id"]
            guid = metadata.get("guid") or episode_id

            if episode_exists(guid):
                skipped += 1
                continue

            insert_episode(metadata)

            inserted += 1

            if inserted % 100 == 0:
                conn.commit()

        except Exception as exc:

            errors += 1

            print(
                f"❌ Failed: "
                f"{metadata_file.name} - {exc}"
            )

    conn.commit()

    print(
        f"✅ {podcast_id}: "
        f"inserted={inserted}, "
        f"skipped={skipped}, "
        f"errors={errors}"
    )

# ============================================================
# MAIN
# ============================================================

def main():

    print("🚀 Starting Metadata → DB indexing")

    try:

        for podcast_id in PODCAST_IDS:
            index_podcast(podcast_id)

    finally:
        conn.close()

    print("\n✅ Indexing complete")

# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()
