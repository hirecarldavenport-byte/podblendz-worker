print("🔥 NEW BLEND ROUTES VERSION ACTIVE")
from typing import Optional
import requests
from fastapi import APIRouter
import uuid
import os
import boto3
from urllib.parse import urlparse

from podpal.semantic.blend_engine import build_blend

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
# ✅ S3 CLIENT (FIXED SIGNATURE VERSION)
# -------------------------------------------------

from botocore.config import Config

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"}  # ✅ CRITICAL FIX
    )
)

BUCKET_NAME = "podblendz-episode-audio"


# -------------------------------------------------
# ✅ PRESIGNED URL GENERATOR (FIXED VERSION)
# -------------------------------------------------
def generate_presigned_url(raw_url: str):
    try:
        parsed = urlparse(raw_url)

        # ✅ robust key extraction
        key = parsed.path.lstrip("/")

        print(f"DEBUG S3 key extracted: {key}")

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )

        print("✅ presigned URL created")

        return presigned_url

    except Exception as e:
        print(f"❌ presigned url failed: {e}")
        return None


# -------------------------------------------------
# ✅ DOWNLOAD HELPER
# -------------------------------------------------
def fetch_to_local(url: str):
    local_file = f"/tmp/{uuid.uuid4().hex}.mp3"

    print(f"⬇️ fetching via boto3: {url}")

    try:
        # ✅ Extract S3 key
        from urllib.parse import urlparse
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")

        print(f"DEBUG key: {key}")

        # ✅ Direct S3 fetch (bypasses 403 issue entirely)
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
        # ✅ STEP 1: Build semantic sequence
        sequence = build_blend(theme_index=theme_index)

        print(f"DEBUG sequence length: {len(sequence)}")

        if not sequence:
            print("❌ No sequence returned")
            return {
                "mode": "semantic_blend",
                "steps": 0,
                "segments": [],
                "final_audio": None,
            }

        # ✅ STEP 2: Extract clip segments
        clips = [
            step["content"]
            for step in sequence
            if step.get("type") == "clip"
        ]

        print(f"✅ clips found: {len(clips)}")

        # ✅ STEP 3: Download + Trim clips
        audio_files = []

        for idx, clip in enumerate(clips):
            print(f"\n--- Processing clip {idx} ---")

            url = clip.get("audio_path")

            if not url:
                print("❌ Missing audio_path")
                continue

            local_file = fetch_to_local(url)

            if not local_file:
                print("❌ Download failed")
                continue

            start = clip.get("start", 0)
            end = clip.get("end", start + 10)
            duration = end - start

            print(f"DEBUG start={start}, end={end}, duration={duration}")

            trimmed_file = f"/tmp/{uuid.uuid4().hex}.mp3"

            try:
                import subprocess
                import imageio_ffmpeg

                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

                print("🎧 trimming clip...")

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

                print(f"✅ trimmed file: {trimmed_file}")
                audio_files.append(trimmed_file)

            except Exception as e:
                print(f"❌ trimming failed: {e}")
                print("⚠️ using original file instead")
                audio_files.append(local_file)

        # ✅ DEBUG AUDIO FILE LIST
        print("\n==============================")
        print("DEBUG AUDIO FILES:")
        for f in audio_files:
            print(f)
        print(f"TOTAL FILES: {len(audio_files)}")
        print("==============================\n")

        final_audio = None

        # ✅ STEP 4: Stitch clips
        print("DEBUG stitch_blend exists:", stitch_blend is not None)
        print("DEBUG len(audio_files):", len(audio_files))

        if stitch_blend and len(audio_files) >= 2:
            try:
                print("🎧 starting stitch...")

                filename = stitch_blend(audio_files, minutes or 5)

                print("✅ stitch returned:", filename)

                if filename:
                    final_audio = f"/audio/final/{filename}"
                    print("✅ FINAL AUDIO:", final_audio)
                else:
                    print("❌ stitch returned empty filename")

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








