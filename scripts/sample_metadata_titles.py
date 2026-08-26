from pathlib import Path
import json

root = Path("ingestion/episode_metadata/core_blendz/the_daily")

for f in sorted(root.glob("*.json"))[:20]:
    try:
        j = json.loads(f.read_text(encoding="utf-8"))

        print()
        print("ID:", j.get("episode_id"))
        print("DATE:", j.get("published"))
        print("TITLE:", j.get("title"))

    except Exception:
        pass