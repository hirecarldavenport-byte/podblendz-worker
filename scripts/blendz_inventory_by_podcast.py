from pathlib import Path
import json
from collections import defaultdict

CHUNK_ROOT = Path("chunked_segments")
META_ROOT = Path("ingestion/episode_metadata")

stats = defaultdict(lambda: {"chunked": 0, "metadata": 0})

for chunk_file in CHUNK_ROOT.rglob("*.json"):

    try:
        data = json.loads(chunk_file.read_text(encoding="utf-8"))

        podcast = data.get("podcast", "UNKNOWN")
        category = data.get("category")
        episode_id = data.get("episode_id")

        stats[podcast]["chunked"] += 1

        meta_file = (
            META_ROOT
            / category
            / podcast
            / f"{episode_id}.json"
        )

        if meta_file.exists():
            stats[podcast]["metadata"] += 1

    except Exception:
        pass

print()
print("PODCAST".ljust(30), "CHUNKED".rjust(8), "META".rjust(8))

for podcast, values in sorted(
    stats.items(),
    key=lambda x: x[1]["chunked"],
    reverse=True,
):
    print(
        podcast[:30].ljust(30),
        str(values["chunked"]).rjust(8),
        str(values["metadata"]).rjust(8),
    )