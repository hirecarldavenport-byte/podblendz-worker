import csv
from collections import defaultdict

TRUTH_TABLE = "episodes_truth.csv"

candidates = []
podcast_counts = defaultdict(int)

with open(TRUTH_TABLE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:

        if row["confidence_ready"] == "True":

            candidates.append(row)
            podcast_counts[row["podcast"]] += 1

#
# Write candidate file
#
with open(
    "confidence_candidates.csv",
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "podcast",
            "topic",
            "episode_hash",
            "title",
            "published",
        ],
    )

    writer.writeheader()

    for row in candidates:

        writer.writerow(
            {
                "podcast": row["podcast"],
                "topic": row["topic"],
                "episode_hash": row["episode_hash"],
                "title": row["title"],
                "published": row["published"],
            }
        )

print()
print("CONFIDENCE CANDIDATES")
print("---------------------")
print(f"Candidates: {len(candidates):,}")
print()

for podcast, count in sorted(
    podcast_counts.items(),
    key=lambda x: x[1],
    reverse=True,
):
    print(f"{podcast}: {count}")

print()
print("Output: confidence_candidates.csv")