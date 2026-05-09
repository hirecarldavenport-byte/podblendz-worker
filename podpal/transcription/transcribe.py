"""
Transcription Module

✅ Uses Whisper
✅ Transcribes local audio files
✅ Saves structured JSON transcripts
"""

import json
from pathlib import Path
import whisper


# ✅ Load model once (important)
model = whisper.load_model("small")


TRANSCRIPT_DIR = Path("transcripts")


def transcribe_audio(audio_path: str, podcast_id: str, episode_id: str):

    print(f"[TRANSCRIBE] Transcribing: {audio_path}")

    result = model.transcribe(audio_path)

    segments = result.get("segments", [])

    transcript_data = {
        "podcast_id": podcast_id,
        "episode_id": episode_id,
        "segments": segments,
    }

    # ✅ Create directory
    out_dir = TRANSCRIPT_DIR / podcast_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{episode_id}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f)

    print(f"[TRANSCRIBE] Saved: {out_file}")

    return str(out_file)
