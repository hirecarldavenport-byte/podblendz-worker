from pathlib import Path
import json
from collections import defaultdict

CHUNK_ROOT = Path("chunked_segments")
META_ROOT = Path("ingestion/episode_metadata")

stats = defaultdict(lambda: {
    "chunked": 0,
    "metadata": 0,
})

for f in CHUNK_ROOT.rglob("*.json"):
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        podcast = data.get("podcast", "UNKNOWN")
        stats[podcast]["chunked"] += 1
    except:
        pass

for f in META_ROOT.rglob("*.json"):
    podcast = f.parent.name
    stats[podcast]["metadata"] += 1

rows = []

for podcast, s in stats.items():
    if s["chunked"] > 0 and s["metadata"] > 0:
        rows.append({
            "podcast": podcast,
            "chunked": s["chunked"],
            "metadata": s["metadata"],
            "score": s["chunked"],
        })

rows.sort(key=lambda x: x["score"], reverse=True)

print()
print("RECOVERY PRIORITY REPORT")
print("=" * 80)

for r in rows:
    print(
        f"{r['podcast']:<30}"
        f"{r['chunked']:>8}"
        f"{r['metadata']:>10}"
    )