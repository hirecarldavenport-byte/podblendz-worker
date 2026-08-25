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

COMMIT_INTERVAL = 100

# ============================================================
# DB
# ============================================================

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")

# ============================================================
# HELPERS
# ============================================================

def insert_episode(metadata: dict) -> bool:
    """
    Returns:
        True  = inserted
        False = duplicate / ignored
    """

    episode_id = metadata["episode_id"]
    guid = metadata.get("guid") or episode_id

    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO episodes (
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

    return cursor.rowcount > 0

# ============================================================
# INDEXING
# ============================================================

def index_podcast(topic: str, podcast_id: str) -> tuple[int, int, int]:

    metadata_dir = (
        METADATA_BASE
        / topic
        / podcast_id
    )

    if not metadata_dir.exists():
        print(
            f"⚠️ Missing metadata folder: "
            f"{metadata_dir}"
        )
        return 0, 0, 0

    inserted = 0
    skipped = 0
    errors = 0

    files = list(metadata_dir.glob("*.json"))

    print(
        f"\n🔍 {topic}/{podcast_id} "
        f"({len(files)} metadata files)"
    )

    for metadata_file in files:

        try:

            with open(
                metadata_file,
                "r",
                encoding="utf-8",
            ) as f:
                metadata = json.load(f)

            was_inserted = insert_episode(metadata)

            if was_inserted:
                inserted += 1
            else:
                skipped += 1

            if inserted % COMMIT_INTERVAL == 0:
                conn.commit()

        except Exception as exc:

            errors += 1

            print(
                f"❌ Failed "
                f"{metadata_file.name}: {exc}"
            )

    conn.commit()

    print(
        f"✅ {topic}/{podcast_id} | "
        f"inserted={inserted} "
        f"skipped={skipped} "
        f"errors={errors}"
    )

    return inserted, skipped, errors

# ============================================================
# DISCOVERY
# ============================================================

def discover_podcasts():

    discovered = []

    for topic_dir in sorted(METADATA_BASE.iterdir()):

        if not topic_dir.is_dir():
            continue

        for podcast_dir in sorted(topic_dir.iterdir()):

            if not podcast_dir.is_dir():
                continue

            discovered.append(
                (
                    topic_dir.name,
                    podcast_dir.name,
                )
            )

    return discovered

# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "🚀 Starting Metadata → DB indexing"
    )

    podcasts = discover_podcasts()

    print(
        f"\nFound {len(podcasts)} podcast folders"
    )

    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    try:

        for topic, podcast_id in podcasts:

            inserted, skipped, errors = (
                index_podcast(
                    topic,
                    podcast_id,
                )
            )

            total_inserted += inserted
            total_skipped += skipped
            total_errors += errors

    finally:
        conn.close()

    print("\n================================================")
   
    print("INDEXING SUMMARY")
    print("================================================")
    print(f"Inserted : {total_inserted}")
    print(f"Skipped  : {total_skipped}")
    print(f"Errors   : {total_errors}")
    print("================================================")

    print("\n✅ Indexing complete")


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()