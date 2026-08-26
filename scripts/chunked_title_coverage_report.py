from pathlib import Path
import json
from collections import defaultdict

CHUNK_ROOT = Path("chunked_segments")
META_ROOT = Path("ingestion/episode_metadata")

chunked_total = 0
exact_matches = 0
podcast_has_metadata = 0
podcast_no_metadata = 0

podcast_stats = defaultdict(
    lambda: {
        "chunked": 0,
        "exact": 0,
        "meta_files": 0,
    }
)

# Build metadata counts by podcast
meta_counts = defaultdict(int)

for meta_file in META_ROOT.rglob("*.json"):
    podcast = meta_file.parent.name
    meta_counts[podcast] += 1

for chunk_file in CHUNK_ROOT.rglob("*.json"):

    try:
        data = json.loads(chunk_file.read_text(encoding="utf-8"))

        podcast = data.get("podcast")
        category = data.get("category")
        episode_id = data.get("episode_id")

        if not podcast:
            podcast = "UNKNOWN"

        chunked_total += 1
        podcast_stats[podcast]["chunked"] += 1

        meta_file = (
            META_ROOT
            / category
            / podcast
            / f"{episode_id}.json"
        )

        if meta_file.exists():
            exact_matches += 1
            podcast_stats[podcast]["exact"] += 1

        if meta_counts[podcast] > 0:
            podcast_has_metadata += 1
        else:
            podcast_no_metadata += 1

    except Exception:
        pass

for podcast, count in meta_counts.items():
    podcast_stats[podcast]["meta_files"] = count

print()
print("BLENDZ TITLE COVERAGE REPORT")
print("=" * 60)

print(f"Chunked Episodes:                    {chunked_total:,}")
print(f"Exact Metadata Matches:             {exact_matches:,}")
print(f"Chunked from Podcasts w/ Metadata:  {podcast_has_metadata:,}")
print(f"Chunked from Podcasts w/o Metadata: {podcast_no_metadata:,}")

print()
print(
    "PODCAST".ljust(35),
    "CHUNKED".rjust(8),
    "EXACT".rjust(8),
    "META".rjust(8),
)

print("-" * 65)

for podcast, stats in sorted(
    podcast_stats.items(),
    key=lambda x: x[1]["chunked"],
    reverse=True,
):
    print(
        podcast[:35].ljust(35),
        str(stats["chunked"]).rjust(8),
        str(stats["exact"]).rjust(8),
        str(stats["meta_files"]).rjust(8),
    )