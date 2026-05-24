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
SEGMENT_PREFIX = "segments/education_learning"
MODEL_NAME = "base"  # ✅ safer + cheaper; switch to medium later if needed

# ============================================================
# GLOBAL SETUP
# ============================================================

s3 = boto3.client("s3")
model = whisper.load_model(MODEL_NAME)

print("✅ Whisper model loaded")
print("✅ S3 connected")

# ============================================================
# HELPERS
# ============================================================

def already_processed(episode_id: str, podcast_id: str) -> bool:
    key = f"{SEGMENT_PREFIX}/{podcast_id}/{episode_id}.json"

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
# SEGMENT CLEANER (VERY IMPORTANT)
# ============================================================

def clean_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []

    for idx, seg in enumerate(raw_segments):

        if not isinstance(seg, dict):
            continue

        text = str(seg.get("text", "")).strip()

        # ✅ remove junk segments
        if len(text) < 15:
            continue

        start = float(seg.get("start", 0))
        end = float(seg.get("end", 0))

        if end - start < 2:  # ❌ very short audio
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

    episode_id: str = payload["episode_id"]
    podcast_id: str = payload["podcast_id"]
    audio_s3_key: str = payload["audio_s3_key"]
    language: str = payload.get("language", "en")

    print(f"\n🎧 Processing: {podcast_id}/{episode_id}")

    # ✅ skip if already done
    if already_processed(episode_id, podcast_id):
        print("⏭️ Skipping (already processed)")
        return {
            "status": "skipped",
            "episode_id": episode_id
        }

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / f"{episode_id}.mp3"

            # ✅ 1. DOWNLOAD
            download_audio(audio_s3_key, audio_path)

            # ✅ 2. TRANSCRIBE
            segments = transcribe_audio(audio_path, language)

            if not segments:
                print("⚠️ No valid segments found")

            # ✅ 3. BUILD OUTPUT
            output = {
                "episode_id": episode_id,
                "podcast_id": podcast_id,
                "audio_s3_key": audio_s3_key,
                "model": MODEL_NAME,
                "language": language,
                "segment_count": len(segments),
                "segments": segments,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }

            output_key = f"{SEGMENT_PREFIX}/{podcast_id}/{episode_id}.json"

            # ✅ 4. SAVE TO S3 (CRITICAL)
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