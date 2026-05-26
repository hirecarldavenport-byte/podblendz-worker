import os
import tempfile
import traceback
import requests
import json
import boto3
import runpod
from faster_whisper import WhisperModel

# -------------------------
# Model initialization
# -------------------------
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")
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
        input_data = job.get("input", {})

        episode_id = input_data.get("episode_id", "unknown")
        language = input_data.get("language", "en")

        # -------------------------
        # ✅ FLEXIBLE INPUT HANDLING
        # -------------------------
        audio_url = input_data.get("audio_url")

        if not audio_url:
            audio_s3_key = input_data.get("audio_s3_key")

            if not audio_s3_key:
                raise ValueError("Missing audio_url OR audio_s3_key")

            bucket = "podblendz-episode-audio"
            audio_url = f"https://{bucket}.s3.amazonaws.com/{audio_s3_key}"

            print("🔁 Converted S3 key → URL")

        print(f"🎧 Starting transcription: {episode_id}")
        print(f"🌐 Audio source: {audio_url}")

        # -------------------------
        # Download audio
        # -------------------------
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
            audio_path = tmp.name

            print("⬇️ Downloading audio...")

            response = requests.get(audio_url, stream=True, timeout=60)
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
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

        # -------------------------
        # ✅ Save to S3 (PERSISTENCE)
        # -------------------------
        try:
            s3 = boto3.client("s3")

            bucket = "podblendz-episode-audio"
            key = f"segments/education_learning/hidden_brain/{episode_id}.json"

            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(result),
                ContentType="application/json"
            )

            print(f"✅ Saved to S3: {key}")

        except Exception as e:
            print("🔥 FAILED TO SAVE TO S3")
            traceback.print_exc()

        # -------------------------
        # ✅ Cleanup temp file
        # -------------------------
        try:
            os.remove(audio_path)
            print("🧹 Temp file removed")
        except Exception:
            pass

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
# RUNPOD ENTRYPOINT ✅ REQUIRED
# -------------------------
runpod.serverless.start({
    "handler": handler
})
print("🚀 New deploy trigger")
