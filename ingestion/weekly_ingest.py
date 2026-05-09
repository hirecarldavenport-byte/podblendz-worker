print("##### NEW PIPELINE FILE RUNNING #####")

import os
print("RUNNING FILE:", os.path.abspath(__file__))


from podpal.transcription.transcribe import transcribe_audio

def test_transcription():

    print("\n=== TESTING TRANSCRIPTION PIPELINE ===")

    audio_path = "local_audio/core_blendz/econtalk/8c42c63abf996f8bff0aed6dc1b719a1.mp3"

    print("[TEST] Using audio:", audio_path)

    transcript_path = transcribe_audio(
        audio_path=audio_path,
        podcast_id="econtalk",
        episode_id="test_run"
    )

    print("[SUCCESS] Transcript saved:", transcript_path)


if __name__ == "__main__":
    test_transcription()
