import json
import random
import statistics
import boto3

BUCKET = "podblendz-episode-audio"
SAMPLE_FILES = 100

s3 = boto3.client("s3")

word_counts = []
durations = []
files = []

print("🔍 Scanning S3 segment files...")

paginator = s3.get_paginator("list_objects_v2")

for page in paginator.paginate(
    Bucket=BUCKET,
    Prefix="segments/"
):
    for obj in page.get("Contents", []):
        key = obj["Key"]

        if key.endswith(".json"):
            files.append(key)

print(f"✅ Found {len(files)} segment files")

if not files:
    raise RuntimeError("No segment files found")

sample_size = min(SAMPLE_FILES, len(files))

sample_files = random.sample(files, sample_size)

print(f"✅ Sampling {sample_size} files")

for key in sample_files:

    try:
        obj = s3.get_object(
            Bucket=BUCKET,
            Key=key
        )

        data = json.loads(
            obj["Body"].read()
        )

        segments = data.get("segments", [])

        for seg in segments:

            text = (
                seg.get("text", "")
                .strip()
            )

            start = seg.get("start")
            end = seg.get("end")

            if (
                not text
                or start is None
                or end is None
            ):
                continue

            words = len(text.split())
            duration = float(end) - float(start)

            word_counts.append(words)
            durations.append(duration)

    except Exception as e:
        print(f"⚠️ Failed: {key}")
        print(e)

print("\n===== SEGMENT STATS =====")

print(f"Segments analyzed: {len(word_counts):,}")

if word_counts:

    print(
        f"Average words: "
        f"{statistics.mean(word_counts):.2f}"
    )

    print(
        f"Median words: "
        f"{statistics.median(word_counts):.2f}"
    )

    print(
        f"Min words: {min(word_counts)}"
    )

    print(
        f"Max words: {max(word_counts)}"
    )

if durations:

    print(
        f"Average duration: "
        f"{statistics.mean(durations):.2f}s"
    )

    print(
        f"Median duration: "
        f"{statistics.median(durations):.2f}s"
    )

    print(
        f"Min duration: "
        f"{min(durations):.2f}s"
    )

    print(
        f"Max duration: "
        f"{max(durations):.2f}s"
    )

short_segments = sum(
    1 for w in word_counts
    if w < 20
)

pct_short = (
    short_segments / len(word_counts) * 100
    if word_counts else 0
)

print(
    f"\n<20 word segments: "
    f"{short_segments:,} "
    f"({pct_short:.1f}%)"
)

