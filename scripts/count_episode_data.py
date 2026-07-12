# scripts/count_episode_data.py

import sqlite3

conn = sqlite3.connect("podblendz.db")

print(
    "titles:",
    conn.execute(
        """
        SELECT COUNT(*)
        FROM episodes
        WHERE title IS NOT NULL
        AND TRIM(title) <> ''
        """
    ).fetchone()[0]
)

print(
    "audio_urls:",
    conn.execute(
        """
        SELECT COUNT(*)
        FROM episodes
        WHERE audio_url IS NOT NULL
        """
    ).fetchone()[0]
)

print(
    "published:",
    conn.execute(
        """
        SELECT COUNT(*)
        FROM episodes
        WHERE published_at IS NOT NULL
        """
    ).fetchone()[0]
)

conn.close()