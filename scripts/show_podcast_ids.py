import sqlite3

conn = sqlite3.connect("podblendz.db")

for row in conn.execute("SELECT * FROM podcasts"):
    print(row)

conn.close()