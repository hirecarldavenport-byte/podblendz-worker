import sqlite3

conn = sqlite3.connect("podblendz.db")

for row in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
):
    print(row[0])

conn.close()