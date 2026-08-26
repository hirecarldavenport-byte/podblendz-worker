from pathlib import Path
from collections import defaultdict

CHUNK_ROOT = Path("chunked_segments")
META_ROOT = Path("ingestion/episode_metadata")

chunk_counts = defaultdict(int)
meta_counts = defaultdict(int)

# Count chunked episodes
for f in CHUNK_ROOT.rglob("*.json"):
    podcast = f.parent.name
    chunk_counts[podcast] += 1

# Count metadata episodes
for f in META_ROOT.rglob("*.json"):
    podcast = f.parent.name
    meta_counts[podcast] += 1

all_podcasts = sorted(
    set(chunk_counts.keys()) | set(meta_counts.keys())
)

print()
print("PODCAST".ljust(35), "CHUNKED".rjust(10), "METADATA".rjust(10))
print("-" * 60)

for podcast in all_podcasts:
    print(
        podcast[:35].ljust(35),
        str(chunk_counts[podcast]).rjust(10),
        str(meta_counts[podcast]).rjust(10),
    )