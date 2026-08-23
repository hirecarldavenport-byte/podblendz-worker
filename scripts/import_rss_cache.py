import json
import sqlite3

DB = "podblendz.db"

conn = sqlite3.connect(DB)

with open("rss_episode_cache.json") as f:
    rss = json.load(f)

conn.execute("""
CREATE TABLE IF NOT EXISTS rss_cache (
    podcast_id TEXT,
    title TEXT,
    guid TEXT,
    rss_id TEXT,
    published TEXT,
    audio_url TEXT,
    link TEXT
)
""")

for row in rss:
    conn.execute("""
    INSERT INTO rss_cache (
        podcast_id,
        title,
        guid,
        rss_id,
        published,
        audio_url,
        link
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        row.get("podcast_id"),
        row.get("title"),
        row.get("guid"),
        row.get("rss_id"),
        row.get("published"),
        row.get("audio_url"),
        row.get("link"),
    ))

conn.commit()

count = conn.execute(
    "SELECT COUNT(*) FROM rss_cache"
).fetchone()[0]

print("Imported:", count)

conn.close()