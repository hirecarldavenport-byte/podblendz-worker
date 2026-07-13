import csv
import json
import re
from pathlib import Path

RAW_AUDIO_INVENTORY = "raw_audio_inventory.txt"
SEGMENTS_INVENTORY = "segments_inventory.txt"
METADATA_ROOT = Path("ingestion/episode_metadata")

inventory = {}

#
# AUDIO
#
audio_re = re.compile(
    r"raw_audio/([^/]+)/([^/]+)/([a-f0-9]+)\.mp3",
    re.IGNORECASE,
)

with open(RAW_AUDIO_INVENTORY, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = audio_re.search(line)

        if not m:
            continue

        topic, podcast, episode_hash = m.groups()

        inventory.setdefault(
            episode_hash,
            {
                "topic": topic,
                "podcast": podcast,
                "episode_hash": episode_hash,
                "audio_exists": True,
                "segment_exists": False,
                "metadata_exists": False,
                "title": "",
                "published": "",
            },
        )

#
# SEGMENTS
#
segment_re = re.compile(
    r"segments/([^/]+)/([^/]+)/([a-f0-9]+)\.json",
    re.IGNORECASE,
)

with open(SEGMENTS_INVENTORY, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = segment_re.search(line)

        if not m:
            continue

        topic, podcast, episode_hash = m.groups()

        record = inventory.setdefault(
            episode_hash,
            {
                "topic": topic,
                "podcast": podcast,
                "episode_hash": episode_hash,
                "audio_exists": False,
                "segment_exists": False,
                "metadata_exists": False,
                "title": "",
                "published": "",
            },
        )

        record["segment_exists"] = True

#
# METADATA
#
if METADATA_ROOT.exists():

    for meta_file in METADATA_ROOT.rglob("*.json"):

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            episode_hash = data.get("episode_id")

            if not episode_hash:
                continue

            record = inventory.setdefault(
                episode_hash,
                {
                    "topic": data.get("master_topic", ""),
                    "podcast": data.get("podcaster_id", ""),
                    "episode_hash": episode_hash,
                    "audio_exists": False,
                    "segment_exists": False,
                    "metadata_exists": False,
                    "title": "",
                    "published": "",
                },
            )

            record["metadata_exists"] = True
            record["title"] = data.get("title", "")
            record["published"] = data.get("published", "")

        except Exception as exc:
            print(f"ERROR reading {meta_file}: {exc}")

#
# WRITE CSV
#
with open(
    "master_inventory.csv",
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "topic",
            "podcast",
            "episode_hash",
            "audio_exists",
            "segment_exists",
            "metadata_exists",
            "title",
            "published",
        ],
    )

    writer.writeheader()

    for row in inventory.values():
        writer.writerow(row)

#
# SUMMARY
#
audio_count = 0
segment_count = 0
metadata_count = 0
all_three = 0

for row in inventory.values():

    if row["audio_exists"]:
        audio_count += 1

    if row["segment_exists"]:
        segment_count += 1

    if row["metadata_exists"]:
        metadata_count += 1

    if (
        row["audio_exists"]
        and row["segment_exists"]
        and row["metadata_exists"]
    ):
        all_three += 1

print()
print("MASTER INVENTORY COMPLETE")
print("-------------------------")
print(f"Total episodes: {len(inventory):,}")
print(f"Audio files:    {audio_count:,}")
print(f"Segment files:  {segment_count:,}")
print(f"Metadata files: {metadata_count:,}")
print(f"All three:      {all_three:,}")
print()
print("Output: master_inventory.csv")