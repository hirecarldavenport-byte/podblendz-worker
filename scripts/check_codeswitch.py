# scripts/check_codeswitch.py

import sqlite3

conn = sqlite3.connect("podblendz.db")

rows = conn.execute(
    """
    SELECT
        id,
        guid,
        title,
        published_at,
        audio_url
    FROM episodes
    WHERE podcast_id = 'code_switch'
    LIMIT 20
    """
).fetchall()

for row in rows:
    print(row)

conn.close()