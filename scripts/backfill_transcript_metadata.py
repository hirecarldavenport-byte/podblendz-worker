from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


ROOT = Path(__file__).resolve().parents[1]

METADATA_ROOT = ROOT / "ingestion" / "episode_metadata"
TRANSCRIPTS = ROOT / "transcripts"


def load_metadata() -> Dict[str, dict]:
    """
    Build lookup:

        episode_id -> metadata json
    """

    lookup: Dict[str, dict] = {}

    for path in METADATA_ROOT.rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            episode_id = data.get("episode_id")

            if episode_id:
                lookup[episode_id] = data

        except Exception as e:
            print(f"⚠️ Bad metadata file: {path} -> {e}")

    return lookup


def update_transcript(
    transcript_path: Path,
    metadata_lookup: Dict[str, dict],
) -> tuple[bool, str]:

    try:
        with open(
            transcript_path,
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

    except Exception as e:
        return False, f"Failed to read: {e}"

    episode_id = data.get("episode_id")

    if not episode_id:
        return False, "Missing episode_id"

    metadata = metadata_lookup.get(episode_id)

    if not metadata:
        return False, "No metadata match"

    changed = False

    # --------------------------------------------------
    # Title
    # --------------------------------------------------

    if not data.get("title"):
        title = metadata.get("title")

        if title:
            data["title"] = title
            changed = True

    # --------------------------------------------------
    # Published
    # --------------------------------------------------

    if not data.get("published"):
        published = metadata.get("published")

        if published:
            data["published"] = published
            changed = True

    # --------------------------------------------------
    # Description
    # --------------------------------------------------

    if not data.get("description"):
        description = metadata.get("description")

        if description:
            data["description"] = description
            changed = True

    # --------------------------------------------------
    # Podcast title
    # --------------------------------------------------

    if not data.get("podcast_title"):
        podcast_title = (
            metadata.get("podcast", {})
            .get("title")
        )

        if podcast_title:
            data["podcast_title"] = podcast_title
            changed = True

    if changed:
        with open(
            transcript_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        return True, "Updated"

    return False, "Already complete"


def main():

    print("\n🚀 BACKFILLING TRANSCRIPT METADATA\n")

    if not METADATA_ROOT.exists():
        raise FileNotFoundError(
            f"Metadata directory not found:\n{METADATA_ROOT}"
        )

    metadata_lookup = load_metadata()

    print(
        f"✅ Loaded {len(metadata_lookup):,} metadata records"
    )

    transcript_files = sorted(
        TRANSCRIPTS.rglob("*.json")
    )

    print(
        f"✅ Found {len(transcript_files):,} transcripts"
    )

    updated = 0
    already_complete = 0
    missing_match = 0
    errors = 0

    for path in transcript_files:

        success, message = update_transcript(
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
            missing_match += 1

        else:
            errors += 1
            print(f"❌ {rel} -> {message}")

    print("\n==============================")
    print("BACKFILL COMPLETE")
    print("==============================")
    print(f"Updated:          {updated:,}")
    print(f"Already Complete: {already_complete:,}")
    print(f"No Metadata:      {missing_match:,}")
    print(f"Errors:           {errors:,}")
    print("==============================\n")


if __name__ == "__main__":
    main() 