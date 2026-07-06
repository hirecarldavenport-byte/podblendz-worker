"""
Transcription Module

✅ Uses Whisper
✅ Transcribes local audio files
✅ Loads episode metadata
✅ Preserves title/published data
✅ Saves structured JSON transcripts
"""

import json
from pathlib import Path

import whisper


# =================================================
# CONFIG
# =================================================

TRANSCRIPT_DIR = Path("transcripts")
EPISODE_METADATA_BASE = Path("ingestion/episode_metadata")


# =================================================
# WHISPER MODEL
# =================================================

# ✅ Load model once (important)
model = whisper.load_model("small")


# =================================================
# METADATA HELPERS
# =================================================

def load_episode_metadata(episode_id: str) -> dict:
    """
    Find the metadata file created by rss_to_s3.py
    and return its contents.
    """

    try:
        matches = list(
            EPISODE_METADATA_BASE.rglob(
                f"{episode_id}.json"
            )
        )

        if not matches:
            print(
                f"⚠️ Metadata not found for "
                f"{episode_id}"
            )
            return {}

        metadata_file = matches[0]

        with open(
            metadata_file,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        print(
            f"⚠️ Failed loading metadata "
            f"for {episode_id}"
        )
        print(e)

        return {}


# =================================================
# TRANSCRIPTION
# =================================================

def transcribe_audio(
    audio_path: str,
    podcast_id: str,
    episode_id: str
):
    print(
        f"[TRANSCRIBE] Transcribing: "
        f"{audio_path}"
    )

    # -----------------------------------------
    # Load episode metadata
    # -----------------------------------------

    metadata = load_episode_metadata(
        episode_id
    )

    print(
        f"[TRANSCRIBE] Title: "
        f"{metadata.get('title')}"
    )

    # -----------------------------------------
    # Whisper
    # -----------------------------------------

    result = model.transcribe(audio_path)

    segments = result.get(
        "segments",
        []
    )

    # -----------------------------------------
    # Transcript payload
    # -----------------------------------------

    transcript_data = {
        "podcast_id": podcast_id,
        "episode_id": episode_id,

        # ✅ Preserve metadata
        "title": metadata.get("title"),
        "published": metadata.get("published"),
        "audio_url": metadata.get("audio_url"),
        "s3_key": metadata.get("s3_key"),

        # ✅ Transcript
        "segments": segments,
    }

    # -----------------------------------------
    # Save transcript
    # -----------------------------------------

    out_dir = TRANSCRIPT_DIR / podcast_id

    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    out_file = (
        out_dir /
        f"{episode_id}.json"
    )

    with open(
        out_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            transcript_data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"[TRANSCRIBE] Saved: "
        f"{out_file}"
    )

    return str(out_file)
