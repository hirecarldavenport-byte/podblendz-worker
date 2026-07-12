from pathlib import Path
import json
import sqlite3

DB_PATH = "podblendz.db"
METADATA_ROOT = Path("ingestion/episode_metadata")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

updated = 0
not_found = 0

for metadata_file in METADATA_ROOT.rglob("*.json"):
    try:
        data = json.loads(
            metadata_file.read_text(encoding="utf-8")
        )

        episode_id = data.get("episode_id")

        if not episode_id:
            continue

        cur.execute(
            """
            UPDATE episodes
            SET
                title = COALESCE(?, title),
                published_at = COALESCE(?, published_at),
                audio_url = COALESCE(?, audio_url)
            WHERE episode_id = ?
            """,
            (
                data.get("title"),
                data.get("published"),
                data.get("audio_url"),
                episode_id,
            ),
        )

        if cur.rowcount:
            updated += cur.rowcount
        else:
            not_found += 1

    except Exception as exc:
        print(f"Failed: {metadata_file} -> {exc}")

conn.commit()

print(f"Updated rows: {updated}")
print(f"No matching episode: {not_found}")

conn.close()