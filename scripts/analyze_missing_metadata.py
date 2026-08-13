from pathlib import Path
from collections import Counter
import json


ROOT = Path(__file__).resolve().parents[1]

CHUNK_ROOT = ROOT / "chunked_segments"
METADATA_ROOT = ROOT / "ingestion" / "episode_metadata"


def load_metadata_by_podcast():
    data = {}

    for path in METADATA_ROOT.rglob("*.json"):

        try:
            with open(path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        except Exception:
            continue

        podcast_dir = path.parent.name

        data.setdefault(podcast_dir, 0)
        data[podcast_dir] += 1

    return data


def load_chunks_by_podcast():
    data = {}

    for path in CHUNK_ROOT.rglob("*.json"):

        try:
            with open(path, "r", encoding="utf-8") as f:
                chunk = json.load(f)

            podcast = chunk.get("podcast")

            if podcast:
                data.setdefault(podcast, 0)
                data[podcast] += 1

        except Exception:
            pass

    return data


def main():

    metadata = load_metadata_by_podcast()
    chunks = load_chunks_by_podcast()

    podcasts = sorted(
        set(metadata.keys()) | set(chunks.keys())
    )

    print()
    print("PODCAST COVERAGE REPORT")
    print("=" * 80)

    for podcast in podcasts:

        chunk_count = chunks.get(podcast, 0)
        metadata_count = metadata.get(podcast, 0)

        print(
            f"{podcast:<35} "
            f"chunks={chunk_count:<6} "
            f"metadata={metadata_count:<6}"
        )


if __name__ == "__main__":
    main()