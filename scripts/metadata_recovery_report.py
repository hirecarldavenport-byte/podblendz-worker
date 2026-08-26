from pathlib import Path
import json
from collections import defaultdict

CHUNK_ROOT = Path("chunked_segments")
META_ROOT = Path("ingestion/episode_metadata")

stats = defaultdict(
    lambda: {
        "chunked": 0,
        "metadata": 0,
        "recoverable": 0,
    }
)

# Count metadata files by podcast
for meta_file in META_ROOT.rglob("*.json"):
    podcast = meta_file.parent.name
    stats[podcast]["metadata"] += 1

# Count chunked files by podcast
for chunk_file in CHUNK_ROOT.rglob("*.json"):
    try:
        data = json.loads(chunk_file.read_text(encoding="utf-8"))

        podcast = data.get("podcast", "UNKNOWN")

        stats[podcast]["chunked"] += 1

        if stats[podcast]["metadata"] > 0:
            stats[podcast]["recoverable"] += 1

    except Exception:
        pass

print()
print("METADATA RECOVERY REPORT")
print("=" * 90)

total_chunked = 0
recoverable = 0
not_recoverable = 0

print(
    "PODCAST".ljust(35),
    "CHUNKED".rjust(8),
    "META".rjust(8),
    "RECOVER".rjust(10),
)

print("-" * 90)

for podcast, values in sorted(
    stats.items(),
    key=lambda x: x[1]["chunked"],
    reverse=True,
):
    c = values["chunked"]
    m = values["metadata"]
    r = values["recoverable"]

    total_chunked += c

    if m > 0:
        recoverable += c
    else:
        not_recoverable += c

    if c > 0:
        print(
            podcast[:35].ljust(35),
            str(c).rjust(8),
            str(m).rjust(8),
            str(r).rjust(10),
        )

print()
print("=" * 90)
print(f"Total chunked episodes      : {total_chunked:,}")
print(f"Recoverable episodes        : {recoverable:,}")
print(f"No metadata catalog exists  : {not_recoverable:,}")

if total_chunked:
    print(
        f"Recovery potential          : "
        f"{recoverable / total_chunked * 100:.1f}%"
    )