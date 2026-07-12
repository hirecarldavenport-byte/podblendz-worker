import sqlite3

conn = sqlite3.connect("podblendz.db")

rows = conn.execute(
    """
    SELECT id, title
    FROM episodes
    WHERE audio_url LIKE ?
    """,
    ("%f050fe0a-fed5-42d5-88d5-60cc6e2fadb5%",)
).fetchall()

print(rows)

conn.close()