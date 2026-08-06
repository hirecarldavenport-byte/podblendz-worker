import csv
from collections import defaultdict

MASTER_INVENTORY = "master_inventory.csv"

stats = defaultdict(
    lambda: {
        "audio": 0,
        "segments": 0,
        "metadata": 0,
    }
)

with open(
    MASTER_INVENTORY,
    newline="",
    encoding="utf-8",
) as f:
    reader = csv.DictReader(f)

    for row in reader:
        podcast = row["podcast"].strip()

        if row["audio_exists"] == "True":
            stats[podcast]["audio"] += 1

        if row["segment_exists"] == "True":
            stats[podcast]["segments"] += 1

        if row["metadata_exists"] == "True":
            stats[podcast]["metadata"] += 1

rows = []

for podcast, values in stats.items():
    audio = values["audio"]
    segments = values["segments"]
    metadata = values["metadata"]

    gap = max(audio - metadata, 0)

    coverage = 0.0
    if audio:
        coverage = (metadata / audio) * 100

    rows.append(
        {
            "podcast": podcast,
            "audio": audio,
            "segments": segments,
            "metadata": metadata,
            "gap": gap,
            "coverage": coverage,
        }
    )

rows.sort(
    key=lambda r: r["gap"],
    reverse=True,
)

print()
print("METADATA GAP REPORT")
print("=" * 110)
print(
    f"{'PODCAST':30}"
    f"{'AUDIO':>10}"
    f"{'SEGMENTS':>12}"
    f"{'METADATA':>12}"
    f"{'GAP':>12}"
    f"{'COVERAGE':>12}"
)
print("-" * 110)

for r in rows:
    print(
        f"{r['podcast'][:30]:30}"
        f"{r['audio']:10,}"
        f"{r['segments']:12,}"
        f"{r['metadata']:12,}"
        f"{r['gap']:12,}"
        f"{r['coverage']:11.1f}%"
    )

total_audio = sum(r["audio"] for r in rows)
total_metadata = sum(r["metadata"] for r in rows)

overall_coverage = (
    (total_metadata / total_audio) * 100
    if total_audio
    else 0
)

print()
print("SUMMARY")
print("=" * 110)
print(f"Audio Episodes:       {total_audio:,}")
print(f"Metadata Episodes:    {total_metadata:,}")
print(f"Metadata Coverage:    {overall_coverage:.2f}%")