import sqlite3

conn = sqlite3.connect("podblendz.db")

rows = conn.execute("""
SELECT podcast_id, COUNT(*)
FROM episodes
GROUP BY podcast_id
ORDER BY COUNT(*) DESC
LIMIT 100
""").fetchall()

for row in rows:
    print(row)

conn.close()