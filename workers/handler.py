print("🚀 HANDLER FILE STARTED")

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import boto3
import runpod
import whisper

# ============================================================
# CONFIG
# ============================================================

BUCKET = "podblendz-episode-audio"
SEGMENT_PREFIX = "segments"
MODEL_NAME = "base"

# ============================================================
# GLOBALS (SAFE INIT)
# ============================================================

model = None
s3 = None

print("✅ Globals initialized")

# ============================================================
# HELPERS
# ============================================================

def get_s3():
    global s3
    if s3 is None:
        print("🔌 Connecting to S3...")
        s3 = boto3.client("s3")
    return s3


def get_model():
    global model
    if model is None:
        print("⚠️ Loading Whisper model...")
        model = whisper.load_model(MODEL_NAME)
        print("✅ Whisper model loaded")
    return model


def already_processed(category: str, podcast: str, episode_id: str) -> bool:
    key = f"{SEGMENT_PREFIX}/{category}/{podcast}/{episode_id}.json"

    try:
        s3_client = get_s3()
        s3_client.head_object(Bucket=BUCKET, Key=key)
        return True
    except Exception as e:
        print(f"⚠️ S3 check failed (treated as not processed): {e}")
        return False


def download_audio(s3_key: str, local_path: Path):
    print("⬇️ Downloading from S3:", s3_key)
    s3_client = get_s3()
    s3_client.download_file(BUCKET, s3_key, str(local_path))


# ============================================================
# SEGMENT CLEANER
# ============================================================

def clean_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []

    for seg in raw_segments:
        if not isinstance(seg, dict):
            continue

        text = str(seg.get("text", "")).strip()
        if len(text) < 15:
            continue

        start = float(seg.get("start", 0))
        end = float(seg.get("end", 0))

        if end - start < 2:
            continue

        cleaned.append({
            "segment_id": str(uuid.uuid4()),
            "text": text,
            "start": start,
            "end": end,
            "duration": round(end - start, 2)
        })

    return cleaned


# ============================================================
# TRANSCRIPTION
# ============================================================

def transcribe_audio(audio_path: Path, language: str):
    model_instance = get_model()

    result: Dict[str, Any] = model_instance.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        fp16=True
    )

    return clean_segments(result.get("segments", []))


# ============================================================
# RUNPOD HANDLER
# ============================================================

def handler(job):
    try:
        payload = job["input"]

        print("🔥 PAYLOAD RECEIVED:", payload)

        # ✅ Validation
        for field in ["episode_id", "category", "podcast", "audio_s3_key"]:
            if field not in payload:
                raise Exception(f"Missing {field}")

        episode_id = payload["episode_id"]
        category = payload["category"]
        podcast = payload["podcast"]
        audio_s3_key = payload["audio_s3_key"]
        language = payload.get("language", "en")

        print(f"🎧 Processing: {category}/{podcast}/{episode_id}")

        # ✅ Skip duplicates
        if already_processed(category, podcast, episode_id):
            print("⏭️ Skipping (already processed)")
            return {
                "status": "COMPLETED",
                "output": {"status": "skipped"}
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / f"{episode_id}.mp3"

            print("⬇️ Downloading audio...")
            download_audio(audio_s3_key, audio_path)

            print("🧠 Running Whisper...")
            segments = transcribe_audio(audio_path, language)

            print(f"✅ Segments created: {len(segments)}")

            output = {
                "episode_id": episode_id,
                "podcast": podcast,
                "category": category,
                "audio_s3_key": audio_s3_key,
                "model": MODEL_NAME,
                "language": language,
                "segment_count": len(segments),
                "segments": segments,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }

            output_key = f"{SEGMENT_PREFIX}/{category}/{podcast}/{episode_id}.json"

            print("🚨 FINAL OUTPUT KEY:", output_key)

            s3_client = get_s3()
            s3_client.put_object(
                Bucket=BUCKET,
                Key=output_key,
                Body=json.dumps(output, indent=2).encode("utf-8"),
                ContentType="application/json"
            )

            print("✅ DIRECT SAVE COMPLETE:", output_key)

        return {
            "status": "COMPLETED",
            "output": {
                "episode_id": episode_id,
                "segment_count": len(segments),
                "s3_output": output_key
            }
        }

    except Exception as e:
        print("🔥 ERROR:", str(e))

        return {
            "status": "FAILED",
            "error": str(e)
        }


# ============================================================
# ENTRYPOINT
# ============================================================

runpod.serverless.start({
    "handler": handler
})
