print("##### CORRECT WEEKLY INGEST NOW RUNNING #####")

print("##### CORRECT WEEKLY INGEST NOW RUNNING #####")

import sys
import os
from pathlib import Path

# ✅ FIX: Add project root to Python path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

print("RUNNING FILE:", os.path.abspath(__file__))

# ✅ NOW imports work
from podpal.transcription.transcribe import transcribe_audio
print("RUNNING FILE:", os.path.abspath(__file__))

from podpal.transcription.transcribe import transcribe_audio

def test_transcription():

    print("\n=== TESTING TRANSCRIPTION PIPELINE ===")

    audio_path = "local_audio/core_blendz/econtalk/8c42c63abf996f8bff0aed6dc1b719a1.mp3"

    print("[TEST] Using audio:", audio_path)

    transcript_path = transcribe_audio(
        audio_path=audio_path,
        podcast_id="econtalk",
        episode_id="manual_test"
    )

    print("[SUCCESS] Transcript saved:", transcript_path)


if __name__ == "__main__":
    test_transcription()
