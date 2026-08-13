from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


ROOT = Path(__file__).resolve().parents[1]

CHUNK_ROOT = ROOT / "chunked_segments"
METADATA_ROOT = ROOT / "ingestion" / "episode_metadata"


def load_metadata() -> Dict[str, dict]:
    """
    Build lookup:

        episode_id -> metadata json
    """

    lookup: Dict[str, dict] = {}

    count = 0

    for path in METADATA_ROOT.rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            episode_id = data.get("episode_id")

            if not episode_id:
                continue

            lookup[episode_id] = data
            count += 1

        except Exception as e:
            print(f"⚠️ Bad metadata file: {path}")
            print(f"   {e}")

    print(f"✅ Loaded {count:,} metadata records")

    return lookup


def update_chunk_file(
    chunk_file: Path,
    metadata_lookup: Dict[str, dict],
) -> tuple[bool, str]:

    try:
        with open(chunk_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception as e:
        return False, f"Read failure: {e}"

    episode_id = data.get("episode_id")

    if not episode_id:
        return False, "Missing episode_id"

    metadata = metadata_lookup.get(episode_id)

    if not metadata:
        return False, "No metadata match"

    changed = False

    #
    # Episode title
    #
    if not data.get("title"):
        title = metadata.get("title")

        if title:
            data["title"] = title
            changed = True

    #
    # Published date
    #
    if not data.get("published"):
        published = metadata.get("published")

        if published:
            data["published"] = published
            changed = True

    #
    # Description
    #
    if not data.get("description"):
        description = metadata.get("description")

        if description:
            data["description"] = description
            changed = True

    #
    # Podcast title
    #
    if not data.get("podcast_title"):
        podcast_title = (
            metadata.get("podcast", {})
            .get("title")
        )

        if podcast_title:
            data["podcast_title"] = podcast_title
            changed = True

    #
    # Podcast ID
    #
    if not data.get("podcast_id"):
        podcast_id = (
            metadata.get("podcast", {})
            .get("id")
        )

        if podcast_id:
            data["podcast_id"] = podcast_id
            changed = True

    #
    # Audio URL
    #
    if not data.get("audio_url"):
        audio_url = metadata.get("audio_url")

        if audio_url:
            data["audio_url"] = audio_url
            changed = True

    if changed:
        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        return True, "Updated"

    return False, "Already complete"


def main():

    print("\n🚀 BACKFILLING CHUNK METADATA\n")

    if not CHUNK_ROOT.exists():
        raise FileNotFoundError(
            f"Chunk directory not found:\n{CHUNK_ROOT}"
        )

    if not METADATA_ROOT.exists():
        raise FileNotFoundError(
            f"Metadata directory not found:\n{METADATA_ROOT}"
        )

    metadata_lookup = load_metadata()

    chunk_files = sorted(
        CHUNK_ROOT.rglob("*.json")
    )

    print(f"✅ Found {len(chunk_files):,} chunk files")

    updated = 0
    already_complete = 0
    missing_metadata = 0
    errors = 0

    for path in chunk_files:

        success, message = update_chunk_file(
            path,
            metadata_lookup,
        )

        rel = path.relative_to(ROOT)

        if message == "Updated":
            updated += 1
            print(f"✅ {rel}")

        elif message == "Already complete":
            already_complete += 1

        elif message == "No metadata match":
            missing_metadata += 1

        else:
            errors += 1
            print(f"❌ {rel}")
            print(f"   {message}")

    print("\n==============================")
    print("BACKFILL COMPLETE")
    print("==============================")
    print(f"Updated:          {updated:,}")
    print(f"Already Complete: {already_complete:,}")
    print(f"No Metadata:      {missing_metadata:,}")
    print(f"Errors:           {errors:,}")
    print("==============================\n")


if __name__ == "__main__":
    main()