import csv
from collections import defaultdict

stats = defaultdict(
    lambda: {
        "audio": 0,
        "segments": 0,
        "metadata": 0,
    }
)

with open(
    "master_inventory.csv",
    newline="",
    encoding="utf-8",
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        podcast = row["podcast"]

        if row["audio_exists"] == "True":
            stats[podcast]["audio"] += 1

        if row["segment_exists"] == "True":
            stats[podcast]["segments"] += 1

        if row["metadata_exists"] == "True":
            stats[podcast]["metadata"] += 1

for podcast, values in sorted(
    stats.items(),
    key=lambda x: x[1]["audio"],
    reverse=True,
):
    print(
        f"{podcast:30} "
        f"audio={values['audio']:6} "
        f"segments={values['segments']:6} "
        f"metadata={values['metadata']:6}"
    )