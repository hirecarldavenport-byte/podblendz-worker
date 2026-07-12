import json
from pathlib import Path
import sqlite3

conn = sqlite3.connect("podblendz.db")

sample = next(
    Path("ingestion/episode_metadata").rglob("*.json")
)

data = json.loads(
    sample.read_text(encoding="utf-8")
)

episode_id = data["episode_id"]

print("Episode ID:", episode_id)

row = conn.execute(
    """
    SELECT id, guid, title
    FROM episodes
    WHERE guid = ?
    """,
    (episode_id,),
).fetchone()

print("GUID Match:", row)

conn.close()