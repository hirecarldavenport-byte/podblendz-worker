from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]

MANIFEST = ROOT / "manifests" / "episode_manifest_clean.jsonl"
TRANSCRIPTS = ROOT / "transcripts"


def load_manifest() -> Dict[str, dict]:
    lookup = {}

    with open(MANIFEST, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)
            except Exception as e:
                print(f"⚠️ Bad manifest row: {e}")
                continue

            episode_id = row.get("episode_id")

            if episode_id:
                lookup[episode_id] = row

    return lookup


def update_transcript(
    transcript_path: Path,
    manifest_lookup: Dict[str, dict]
) -> tuple[bool, str]:

    try:
        with open(
            transcript_path,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except Exception as e:
        return False, f"Failed to read: {e}"

    episode_id = data.get("episode_id")

    if not episode_id:
        return False, "Missing episode_id"

    metadata = manifest_lookup.get(episode_id)

    if not metadata:
        return False, "No manifest match"

    changed = False

    # ----------------------------------------------------
    # Episode title
    # ----------------------------------------------------
    if not data.get("title"):
        title = metadata.get("episode_title")

        if title:
            data["title"] = title
            changed = True

    # ----------------------------------------------------
    # Published
    # ----------------------------------------------------
    if not data.get("published"):
        published = (
            metadata.get("published")
            or metadata.get("published_at")
        )

        if published:
            data["published"] = published
            changed = True

    # ----------------------------------------------------
    # Description
    # ----------------------------------------------------
    if not data.get("description"):
        description = (
            metadata.get("description")
            or metadata.get("episode_description")
        )

        if description:
            data["description"] = description
            changed = True

    # ----------------------------------------------------
    # Podcast title
    # ----------------------------------------------------
    if not data.get("podcast_title"):
        podcast_title = (
            metadata.get("podcast_title")
            or metadata.get("podcast_name")
            or metadata.get("podcast_id")
        )

        if podcast_title:
            data["podcast_title"] = podcast_title
            changed = True

    if changed:
        with open(
            transcript_path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        return True, "Updated"

    return False, "Already complete"


def main():

    print("\n🚀 BACKFILLING TRANSCRIPT METADATA\n")

    if not MANIFEST.exists():
        raise FileNotFoundError(
            f"Manifest not found:\n{MANIFEST}"
        )

    manifest_lookup = load_manifest()

    print(
        f"✅ Loaded {len(manifest_lookup):,} "
        "manifest records"
    )

    transcript_files = sorted(
        TRANSCRIPTS.rglob("*.json")
    )

    print(
        f"✅ Found {len(transcript_files):,} "
        "transcripts"
    )

    updated = 0
    already_complete = 0
    missing_match = 0
    errors = 0

    for path in transcript_files:

        success, message = update_transcript(
            path,
            manifest_lookup
        )

        rel = path.relative_to(ROOT)

        if message == "Updated":
            updated += 1
            print(f"✅ {rel}")

        elif message == "Already complete":
            already_complete += 1

        elif message == "No manifest match":
            missing_match += 1
            print(f"⚠️ No match -> {rel}")

        else:
            errors += 1
            print(f"❌ {rel} -> {message}")

    print("\n==============================")
    print("BACKFILL COMPLETE")
    print("==============================")
    print(f"Updated:          {updated:,}")
    print(f"Already Complete: {already_complete:,}")
    print(f"No Manifest:      {missing_match:,}")
    print(f"Errors:           {errors:,}")
    print("==============================\n")


if __name__ == "__main__":
    main()