import os
import tempfile
import traceback
import requests
import runpod
from faster_whisper import WhisperModel

# -------------------------
# Model initialization
# -------------------------
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")  # ✅ safer
DEVICE = "cuda"
COMPUTE_TYPE = "float16"

try:
    print("✅ Loading Whisper model...")
    model = WhisperModel(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE
    )
    print("✅ Whisper model loaded")

except Exception as e:
    print("🔥 MODEL LOAD FAILED")
    traceback.print_exc()
    raise e


# -------------------------
# Core handler
# -------------------------
def handler(job):
    try:
        input_data = job["input"]

        episode_id = input_data["episode_id"]
        audio_url = input_data["audio_url"]
        language = input_data.get("language", "en")

        print(f"🎧 Starting transcription: {episode_id}")

        # -------------------------
        # Download audio
        # -------------------------
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
            audio_path = tmp.name

            print(f"⬇️ Downloading audio from {audio_url}")

            response = requests.get(audio_url, stream=True, timeout=60)
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)

        # -------------------------
        # Transcribe
        # -------------------------
        print("🧠 Running Whisper...")

        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        transcript_segments = []
        full_text = []

        for seg in segments:
            transcript_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })
            full_text.append(seg.text.strip())

        result = {
            "episode_id": episode_id,
            "language": info.language,
            "duration": info.duration,
            "segments": transcript_segments,
            "text": " ".join(full_text)
        }

        print(f"✅ Completed transcription: {episode_id}")

        return {
            "output": result
        }

    except Exception as e:
        print("🔥 HANDLER CRASH")
        traceback.print_exc()
        return {
            "error": str(e)
        }


# -------------------------
# RUNPOD ENTRYPOINT ✅ CRITICAL
# -------------------------
runpod.serverless.start({
    "handler": handler
})
