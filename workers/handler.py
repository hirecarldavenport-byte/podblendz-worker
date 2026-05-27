print("🔥🔥 HANDLER FILE VERSION 2 LOADED 🔥🔥")
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
SEGMENT_PREFIX = "segments"   # ✅ FIXED (no hardcoding)

MODEL_NAME = "base"  # ✅ can upgrade later

# ============================================================
# GLOBAL SETUP
# ============================================================

s3 = boto3.client("s3")
model = whisper.load_model(MODEL_NAME)

print("✅ Whisper model loaded — NEW FILE")
print("✅ S3 connected")

# ============================================================
# HELPERS
# ============================================================

def already_processed(category: str, podcast: str, episode_id: str) -> bool:
    key = f"{SEGMENT_PREFIX}/{category}/{podcast}/{episode_id}.json"

    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except:
        return False


def download_audio(s3_key: str, local_path: Path):
    s3.download_file(BUCKET, s3_key, str(local_path))


def upload_segments(s3_key: str, data: dict):
    s3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json"
    )

# ============================================================
# SEGMENT CLEANER
# ============================================================

def clean_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []

    for seg in raw_segments:
        if not isinstance(seg, dict):
            continue

        text = str(seg.get("text", "")).strip()

        # ✅ remove very short / junk text
        if len(text) < 15:
            continue

        start = float(seg.get("start", 0))
        end = float(seg.get("end", 0))

        # ✅ remove tiny audio slices
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
    result: Dict[str, Any] = model.transcribe(
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
    payload = job["input"]

    # ✅ FIXED INPUT KEYS
    episode_id: str = payload["episode_id"]
    podcast: str = payload["podcast"]
    category: str = payload["category"]
    audio_s3_key: str = payload["audio_s3_key"]
    language: str = payload.get("language", "en")

    print(f"\n🎧 Processing: {category}/{podcast}/{episode_id}")

    # ✅ DUPLICATE PROTECTION (NOW CORRECT PATH)
    if already_processed(category, podcast, episode_id):
        print("⏭️ Skipping (already processed)")
        return {
            "status": "skipped",
            "episode_id": episode_id
        }

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / f"{episode_id}.mp3"

            # ✅ 1. DOWNLOAD
            print("⬇️ Downloading audio...")
            download_audio(audio_s3_key, audio_path)

            # ✅ 2. TRANSCRIBE
            print("🧠 Running Whisper...")
            segments = transcribe_audio(audio_path, language)

            if not segments:
                print("⚠️ No valid segments found")

            # ✅ 3. BUILD OUTPUT
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

            # ✅ FIXED OUTPUT PATH (CRITICAL)
            output_key = f"{SEGMENT_PREFIX}/{category}/{podcast}/{episode_id}.json"

            print(f"✅ Saving to: {output_key}")

            # ✅ 4. SAVE
            upload_segments(output_key, output)

        print(f"✅ Stored → {output_key}")

        return {
            "status": "success",
            "episode_id": episode_id,
            "segments": len(segments),
            "s3_output": output_key
        }

    except Exception as e:
        print(f"🔥 Error: {e}")

        return {
            "status": "error",
            "episode_id": episode_id,
            "error": str(e)
        }

# ============================================================
# ENTRYPOINT
# ============================================================

runpod.serverless.start({
    "handler": handler
})
