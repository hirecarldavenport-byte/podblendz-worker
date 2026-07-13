import csv
from collections import defaultdict

stats = defaultdict(int)

with open("episodes_truth.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        if row["confidence_ready"] == "True":
            stats[row["podcast"]] += 1

for podcast, count in sorted(
    stats.items(),
    key=lambda x: x[1],
    reverse=True,
):
    print(f"{podcast}: {count}")