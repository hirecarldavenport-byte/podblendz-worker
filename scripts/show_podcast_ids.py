# scripts/show_podcasts.py

import sqlite3

conn = sqlite3.connect("podblendz.db")

for row in conn.execute("""
SELECT id
FROM podcasts
ORDER BY id
"""):
    print(row[0])

conn.close()