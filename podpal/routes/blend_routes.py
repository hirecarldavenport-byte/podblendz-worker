from typing import Optional
from fastapi import APIRouter
import uuid
import os
import boto3
from urllib.parse import urlparse

from podpal.semantic.blend_engine import build_blend

# ✅ DEBUG: Confirm AWS key loads (CRITICAL)
print("🔥 NEW BLEND ROUTES VERSION ACTIVE")
print("AWS KEY LOADED:", os.environ.get("AWS_ACCESS_KEY_ID"))

# -------------------------------------------------
# ✅ SAFE STITCH IMPORT
# -------------------------------------------------
stitch_blend = None

try:
    from podpal.audio.stitch import stitch_blendz
    stitch_blend = stitch_blendz
    print("✅ stitch_blend loaded successfully")
except Exception as e:
    print("⚠️ stitch import failed:", e)

# -------------------------------------------------
# ✅ ROUTER
# -------------------------------------------------
router = APIRouter()
print("✅ blend_routes.py loaded")

# -------------------------------------------------
# ✅ S3 CLIENT (NO HARDCODE — USE ENV VARS)
# -------------------------------------------------
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1",
)

BUCKET_NAME = "podblendz-episode-audio"

# -------------------------------------------------
# ✅ DOWNLOAD HELPER (FINAL VERSION — boto3)
# -------------------------------------------------
def fetch_to_local(url: str):
    local_file = f"/tmp/{uuid.uuid4().hex}.mp3"

    print(f"⬇️ fetching via boto3: {url}")

    try:
        parsed = urlparse(url)
        key = "raw_audio/entrepreneurship/how_i_built_this/000df7db2e3453998677f4663a3b92cd.mp3"

        print(f"DEBUG key: {key}")

        response = s3.get_object(
            Bucket=BUCKET_NAME,
            Key=key
        )

        with open(local_file, "wb") as f:
            f.write(response["Body"].read())

        print(f"✅ saved via boto3: {local_file}")
        return local_file

    except Exception as e:
        print(f"❌ boto3 fetch failed: {e}")
        return None

# -------------------------------------------------
# ✅ /blend ENDPOINT
# -------------------------------------------------
@router.get("/blend")
def get_blend(minutes: Optional[int] = 5, theme_index: Optional[int] = None):

    print("\n🎯 /blend endpoint hit")

    try:
        sequence = build_blend(theme_index=theme_index)

        print(f"DEBUG sequence length: {len(sequence)}")

        if not sequence:
            return {
                "mode": "semantic_blend",
                "steps": 0,
                "segments": [],
                "final_audio": None,
            }

        clips = [
            step["content"]
            for step in sequence
            if step.get("type") == "clip"
        ]

        print(f"✅ clips found: {len(clips)}")

        audio_files = []

        for idx, clip in enumerate(clips):
            print(f"\n--- Processing clip {idx} ---")

            url = clip.get("audio_path")
            if not url:
                continue

            local_file = fetch_to_local(url)

            if not local_file:
                continue

            start = clip.get("start", 0)
            end = clip.get("end", start + 10)
            duration = end - start

            print(f"DEBUG start={start}, duration={duration}")

            trimmed_file = f"/tmp/{uuid.uuid4().hex}.mp3"

            try:
                import subprocess
                import imageio_ffmpeg

                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

                subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-loglevel", "error",
                        "-ss", str(start),
                        "-t", str(min(duration, 6)),
                        "-i", local_file,
                        "-vn",
                        "-acodec", "libmp3lame",
                        trimmed_file,
                    ],
                    check=True,
                )

                print(f"✅ trimmed: {trimmed_file}")
                audio_files.append(trimmed_file)

            except Exception as e:
                print(f"❌ trimming failed: {e}")
                audio_files.append(local_file)

        print("TOTAL FILES:", len(audio_files))

        final_audio = None

        if stitch_blend and len(audio_files) >= 2:
            try:
                print("🎧 starting stitch...")

                filename = stitch_blend(audio_files, minutes or 5)

                print("✅ stitch returned:", filename)

                if filename:
                    final_audio = f"/audio/final/{filename}"

            except Exception as err:
                print("🔥 stitch error:", err)

        else:
            print("⚠️ Not enough files to stitch")

        return {
            "mode": "semantic_blend",
            "steps": len(clips),
            "segments": clips,
            "final_audio": final_audio,
        }

    except Exception as e:
        print("❌ blend error:", e)
        return {
            "mode": "semantic_blend",
            "steps": 0,
            "segments": [],
            "final_audio": None,
            "error": str(e),
        }
