from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


ROOT = Path(__file__).resolve().parents[1]

CHUNK_ROOT = ROOT / "chunked_segments"
METADATA_ROOT = ROOT / "ingestion" / "episode_metadata"

MISSING_REPORT = ROOT / "missing_chunk_metadata.json"


def load_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Build multiple metadata lookup indexes.
    """

    by_episode_id = {}
    by_audio_key = {}

    loaded = 0
    bad_files = 0

    for path in METADATA_ROOT.rglob("*.json"):

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception:
            bad_files += 1
            continue

        loaded += 1

        episode_id = data.get("episode_id")

        if episode_id:
            by_episode_id[episode_id] = data

        audio_key = data.get("audio_s3_key")

        if audio_key:
            by_audio_key[audio_key] = data

    print(f"✅ Loaded metadata records: {loaded:,}")
    print(f"⚠️ Bad metadata files: {bad_files:,}")

    return {
        "episode_id": by_episode_id,
        "audio_key": by_audio_key,
    }


def find_metadata(
    chunk_data: dict,
    metadata_lookup: dict
) -> dict | None:
    """
    Try multiple matching strategies.
    """

    episode_id = chunk_data.get("episode_id")

    if episode_id:
        metadata = (
            metadata_lookup["episode_id"]
            .get(episode_id)
        )

        if metadata:
            return metadata

    audio_key = chunk_data.get("audio_s3_key")

    if audio_key:
        metadata = (
            metadata_lookup["audio_key"]
            .get(audio_key)
        )

        if metadata:
            return metadata

    return None


def enrich_chunk(
    chunk_data: dict,
    metadata: dict
) -> bool:

    changed = False

    if not chunk_data.get("title"):
        title = metadata.get("title")

        if title:
            chunk_data["title"] = title
            changed = True

    if not chunk_data.get("published"):
        published = (
            metadata.get("published")
            or metadata.get("published_at")
        )

        if published:
            chunk_data["published"] = published
            changed = True

    if not chunk_data.get("description"):
        description = (
            metadata.get("description")
            or metadata.get("episode_description")
        )

        if description:
            chunk_data["description"] = description
            changed = True

    if not chunk_data.get("podcast_title"):

        podcast_title = (
            metadata.get("podcast", {})
            .get("title")
        )

        if podcast_title:
            chunk_data["podcast_title"] = podcast_title
            changed = True

    if not chunk_data.get("podcast_id"):

        podcast_id = (
            metadata.get("podcast", {})
            .get("id")
        )

        if podcast_id:
            chunk_data["podcast_id"] = podcast_id
            changed = True

    if not chunk_data.get("audio_url"):

        audio_url = metadata.get("audio_url")

        if audio_url:
            chunk_data["audio_url"] = audio_url
            changed = True

    return changed


def process_file(
    path: Path,
    metadata_lookup: dict
) -> tuple[str, dict | None]:

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception as e:
        return f"ERROR: {e}", None

    metadata = find_metadata(
        data,
        metadata_lookup
    )

    if not metadata:

        return (
            "NO_MATCH",
            {
                "file": str(
                    path.relative_to(ROOT)
                ),
                "episode_id": data.get(
                    "episode_id"
                ),
                "podcast": data.get(
                    "podcast"
                ),
                "category": data.get(
                    "category"
                ),
            },
        )

    changed = enrich_chunk(
        data,
        metadata
    )

    if changed:

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        return "UPDATED", None

    return "ALREADY_COMPLETE", None


def main():

    print()
    print("=" * 60)
    print("BACKFILL CHUNK METADATA")
    print("=" * 60)
    print()

    if not CHUNK_ROOT.exists():
        raise FileNotFoundError(
            f"Chunk root not found: {CHUNK_ROOT}"
        )

    if not METADATA_ROOT.exists():
        raise FileNotFoundError(
            f"Metadata root not found: {METADATA_ROOT}"
        )

    metadata_lookup = load_metadata()

    chunk_files = sorted(
        CHUNK_ROOT.rglob("*.json")
    )

    print(
        f"✅ Chunk files found: "
        f"{len(chunk_files):,}"
    )

    updated = 0
    complete = 0
    missing = 0
    errors = 0

    missing_items = []

    for path in chunk_files:

        status, payload = process_file(
            path,
            metadata_lookup,
        )

        if status == "UPDATED":
            updated += 1

        elif status == "ALREADY_COMPLETE":
            complete += 1

        elif status == "NO_MATCH":
            missing += 1

            if payload:
                missing_items.append(
                    payload
                )

        else:
            errors += 1

    with open(
        MISSING_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            missing_items,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Updated:           {updated:,}")
    print(f"Already Complete:  {complete:,}")
    print(f"No Match:          {missing:,}")
    print(f"Errors:            {errors:,}")
    print()
    print(
        f"Missing Report: {MISSING_REPORT}"
    )
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()