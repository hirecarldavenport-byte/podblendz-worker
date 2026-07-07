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
from typing import Optional

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
    episode_id: str,
    title: Optional[str] = None,
    published: Optional[str] = None,
):
    print(
        f"[TRANSCRIBE] Transcribing: "
        f"{audio_path}"
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
        "title": title,
        "published": published,
        "segments": segments,
        

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
