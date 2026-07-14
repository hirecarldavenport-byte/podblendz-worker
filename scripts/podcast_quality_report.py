# scripts/podcast_quality_report.py

import sqlite3

conn = sqlite3.connect("podblendz.db")

rows = conn.execute("""
SELECT
    podcast_id,
    COUNT(*) AS episodes,
    SUM(
        CASE
            WHEN title != id THEN 1
            ELSE 0
        END
    ) AS titled,
    SUM(
        CASE
            WHEN transcript_status = 'completed' THEN 1
            ELSE 0
        END
    ) AS transcripts
FROM episodes
GROUP BY podcast_id
ORDER BY episodes DESC
""").fetchall()

print()
print(
    f"{'PODCAST':30} "
    f"{'EPISODES':>10} "
    f"{'TITLES':>10} "
    f"{'TRANSCRIPTS':>12}"
)

print("-" * 70)

for podcast, episodes, titles, transcripts in rows:
    print(
        f"{podcast:30} "
        f"{episodes:10,} "
        f"{titles:10,} "
        f"{transcripts:12,}"
    )