import csv

INPUT_FILE = "master_inventory.csv"
OUTPUT_FILE = "episodes_truth.csv"

rows = []

with open(
    INPUT_FILE,
    newline="",
    encoding="utf-8"
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        audio = str(row["audio_exists"]).lower() == "true"
        segments = str(row["segment_exists"]).lower() == "true"
        metadata = str(row["metadata_exists"]).lower() == "true"

        #
        # Confidence engine can only work when
        # we have segments and metadata.
        #
        confidence_ready = segments and metadata

        rows.append(
            {
                "podcast": row["podcast"],
                "topic": row["topic"],
                "episode_hash": row["episode_hash"],
                "audio_exists": audio,
                "segment_exists": segments,
                "metadata_exists": metadata,
                "title": row["title"],
                "published": row["published"],
                "audio_url": row.get("audio_url", ""),
                "confidence_ready": confidence_ready,
            }
        )

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
            "audio_exists",
            "segment_exists",
            "metadata_exists",
            "title",
            "published",
            "audio_url",
            "confidence_ready",
        ],
    )

    writer.writeheader()

    writer.writerows(rows)

print()
print("TRUTH TABLE CREATED")
print("-------------------")
print(f"Episodes: {len(rows):,}")

ready = sum(
    1
    for r in rows
    if r["confidence_ready"]
)

print(
    f"Confidence Ready: {ready:,}"
)

print(
    f"Output: {OUTPUT_FILE}"
)