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
]

# ============================================================
# DB
# ============================================================

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# ============================================================
# HELPERS
# ============================================================

def episode_exists(episode_id: str) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM episodes
            WHERE id = ?
            """,
            (episode_id,),
        ).fetchone()
        is not None
    )


def insert_episode(metadata: dict):

    conn.execute(
        """
        INSERT INTO episodes (
            id,
            guid,
            podcast_id,
            title,
            published_at,
            source_url,
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
            metadata["episode_id"],
            metadata.get("guid")
            or metadata["episode_id"],
            metadata["podcaster_id"],
            metadata.get("title"),
            metadata.get("published"),
            metadata.get("link"),
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

    for metadata_file in metadata_dir.glob("*.json"):

        try:

            with open(
                metadata_file,
                "r",
                encoding="utf-8",
            ) as f:
                metadata = json.load(f)

        except Exception as exc:

            print(
                f"❌ Could not read "
                f"{metadata_file}: {exc}"
            )
            continue

        episode_id = metadata["episode_id"]

        if episode_exists(episode_id):
            skipped += 1
            continue

        insert_episode(metadata)

        inserted += 1

    conn.commit()

    print(
        f"✅ {podcast_id}: "
        f"inserted={inserted}, "
        f"skipped={skipped}"
    )

# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "🚀 Starting Metadata → DB indexing"
    )

    for podcast_id in PODCAST_IDS:

        index_podcast(podcast_id)

    conn.close()

    print(
        "\n✅ Indexing complete"
    )

# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()
