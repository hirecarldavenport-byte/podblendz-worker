import csv
import sqlite3
from pathlib import Path

DB_PATH = Path("podblendz.db")
TRUTH_FILE = "episodes_truth.csv"

conn = sqlite3.connect(DB_PATH)

inserted = 0
updated = 0
skipped = 0

with open(TRUTH_FILE, newline="", encoding="utf-8") as f:

    reader = csv.DictReader(f)

    for row in reader:

        podcast_id = row["podcast"].strip()

        if not podcast_id:
            skipped += 1
            continue

        episode_hash = row["episode_hash"].strip()

        if not episode_hash:
            skipped += 1
            continue

        episode_id = episode_hash

        title = row["title"].strip() or episode_hash

        published = row["published"].strip() or None

        audio_s3_key = (
            f"raw_audio/"
            f"{row['topic']}/"
            f"{podcast_id}/"
            f"{episode_hash}.mp3"
        )

        transcript_status = (
            "completed"
            if row["segment_exists"] == "True"
            else "pending"
        )

        existing = conn.execute(
            """
            SELECT id
            FROM episodes
            WHERE id = ?
            """,
            (episode_id,),
        ).fetchone()

        if existing:

            conn.execute(
                """
                UPDATE episodes
                SET
                    podcast_id = ?,
                    title = ?,
                    published_at = ?,
                    audio_s3_key = ?,
                    transcript_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    podcast_id,
                    title,
                    published,
                    audio_s3_key,
                    transcript_status,
                    episode_id,
                ),
            )

            updated += 1

        else:

            conn.execute(
                """
                INSERT INTO episodes (
                    id,
                    podcast_id,
                    guid,
                    title,
                    published_at,
                    audio_s3_key,
                    storage_tier,
                    transcript_status,
                    ingested_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    's3',
                    ?,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    episode_id,
                    podcast_id,
                    episode_id,
                    title,
                    published,
                    audio_s3_key,
                    transcript_status,
                ),
            )

            inserted += 1

conn.commit()
conn.close()

print()
print("REBUILD COMPLETE")
print("----------------")
print(f"Inserted: {inserted:,}")
print(f"Updated:  {updated:,}")
print(f"Skipped:  {skipped:,}")