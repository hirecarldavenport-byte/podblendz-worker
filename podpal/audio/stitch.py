import os
import uuid
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


# =================================================
# S3 CONFIG
# =================================================

BUCKET_NAME = "podblendz-episode-audio"

s3 = boto3.client("s3")


# =================================================
# DIRECTORIES
# =================================================

BASE_DIR = Path("media")
TEMP_DIR = BASE_DIR / "temp"
FINAL_DIR = BASE_DIR / "final"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)


# =================================================
# HELPERS
# =================================================

def build_public_url(bucket: str, key: str) -> str:
    """
    Build a public S3 URL.
    """
    return f"https://{bucket}.s3.amazonaws.com/{key}"


# =================================================
# MAIN STITCH FUNCTION
# =================================================

def stitch_blendz(audio_files, max_files=20):
    """
    Build a single MP3 from one or more source MP3 files,
    upload it to S3, and return URLs.

    Returns:
    {
        "local_file": "...",
        "s3_key": "...",
        "public_url": "..."
    }
    """

    if not audio_files:
        raise ValueError("No audio files supplied")

    print("\n🎯 Building PodBlend...")

    max_files = max(
        1,
        min(len(audio_files), int(max_files))
    )

    sequence = audio_files[:max_files]

    temp_outputs = []

    # ============================================
    # STEP 1 - RE-ENCODE CLIPS
    # ============================================

    for source_file in sequence:

        if not os.path.exists(source_file):
            print(f"⚠️ Missing file: {source_file}")
            continue

        temp_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

        print(f"🎧 Processing: {source_file}")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_file),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-ab",
                "128k",
                str(temp_file),
            ],
            check=True,
        )

        temp_outputs.append(temp_file)

    if not temp_outputs:
        raise RuntimeError(
            "No valid audio clips were processed"
        )

    # ============================================
    # STEP 2 - CREATE CONCAT FILE
    # ============================================

    concat_file = TEMP_DIR / (
        f"concat_{uuid.uuid4().hex}.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as f:

        for file_path in temp_outputs:

            abs_path = file_path.resolve()

            f.write(
                f"file '{abs_path.as_posix()}'\n"
            )

    # ============================================
    # STEP 3 - FINAL RENDER
    # ============================================

    output_file = FINAL_DIR / (
        f"{uuid.uuid4().hex}.mp3"
    )

    print("🎧 Rendering final audio...")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-acodec",
            "libmp3lame",
            "-b:a",
            "192k",
            str(output_file),
        ],
        check=True,
    )

    print(f"✅ Final MP3: {output_file}")

    # ============================================
    # STEP 4 - UPLOAD TO S3
    # ============================================

    try:

        s3_key = (
            f"final_blends/{output_file.name}"
        )

        print("\n☁️ Uploading to S3...")
        print("Bucket:", BUCKET_NAME)
        print("Key:", s3_key)

        s3.upload_file(
            Filename=str(output_file),
            Bucket=BUCKET_NAME,
            Key=s3_key,
            ExtraArgs={
                "ContentType": "audio/mpeg"
            },
        )

        public_url = build_public_url(
            BUCKET_NAME,
            s3_key
        )

        print("✅ Upload successful")
        print("🔗", public_url)

        return {
            "local_file": str(output_file),
            "s3_key": s3_key,
            "public_url": public_url,
        }

    except ClientError as e:

        print("\n🔥 S3 UPLOAD FAILED 🔥")
        print(str(e))
        raise

    finally:

        try:
            concat_file.unlink(missing_ok=True)
        except Exception:
            pass








