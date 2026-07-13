import csv

TRUTH_TABLE = "episodes_truth.csv"
OUTPUT_FILE = "confidence_report.csv"

results = []

with open(TRUTH_TABLE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:

        score = 0

        #
        # Audio
        #
        if row["audio_exists"] == "True":
            score += 10

        #
        # Metadata
        #
        if row["metadata_exists"] == "True":
            score += 25

        #
        # Segments
        #
        if row["segment_exists"] == "True":
            score += 35

        #
        # Title
        #
        if row["title"].strip():
            score += 15

        #
        # Published Date
        #
        if row["published"].strip():
            score += 15

        results.append(
            {
                "podcast": row["podcast"],
                "topic": row["topic"],
                "episode_hash": row["episode_hash"],
                "title": row["title"],
                "confidence_score": score,
            }
        )

#
# Sort highest confidence first
#
results.sort(
    key=lambda r: r["confidence_score"],
    reverse=True,
)

#
# Export report
#
with open(
    OUTPUT_FILE,
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
            "confidence_score",
        ],
    )

    writer.writeheader()

    writer.writerows(results)

#
# Summary
#
print()
print("CONFIDENCE REPORT CREATED")
print("-------------------------")
print(f"Episodes Scored: {len(results):,}")

top_90 = sum(
    1 for r in results
    if r["confidence_score"] >= 90
)

top_70 = sum(
    1 for r in results
    if r["confidence_score"] >= 70
)

print(f"90+ Confidence: {top_90:,}")
print(f"70+ Confidence: {top_70:,}")

print()
print("Top 20 Episodes")
print("---------------")

for row in results[:20]:
    print(
        f"{row['confidence_score']:3} | "
        f"{row['podcast']:20} | "
        f"{row['title'][:60]}"
    )

print()
print(f"Output: {OUTPUT_FILE}")