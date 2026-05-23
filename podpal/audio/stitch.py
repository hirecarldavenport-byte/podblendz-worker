import os
import uuid
import subprocess
from pathlib import Path
import boto3

# ✅ S3 SETUP
s3 = boto3.client("s3")
BUCKET_NAME = "podblendz-episode-audio"

# ✅ OUTPUT DIRECTORIES (Render-compatible)
BASE_DIR = Path("/app/audio")
TEMP_DIR = BASE_DIR / "temp"
FINAL_DIR = BASE_DIR / "final"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ MAIN STITCH FUNCTION
# -------------------------------------------------

def stitch_blendz(audio_files, minutes=5):

    if not audio_files:
        return None

    print("🎯 Building PodBlend...")

    max_files = max(1, min(len(audio_files), int(minutes)))

    sequence = audio_files * (max_files // len(audio_files) + 1)
    sequence = sequence[:max_files]

    temp_outputs = []

    # -------------------------------------------------
    # ✅ STEP 1 — RE-ENCODE INDIVIDUAL CLIPS
    # -------------------------------------------------

    for file_path in sequence:
        temp_out = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

        print(f"🎧 Processing: {file_path}")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", file_path,
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "128k",
                str(temp_out),
            ],
            check=True,
        )

        temp_outputs.append(temp_out)

    # -------------------------------------------------
    # ✅ STEP 2 — CONCAT FILE LIST
    # -------------------------------------------------

    concat_file = TEMP_DIR / f"concat_{uuid.uuid4().hex}.txt"

    with open(concat_file, "w") as f:
        for fpath in temp_outputs:
            f.write(f"file '{fpath}'\n")

    # -------------------------------------------------
    # ✅ STEP 3 — FINAL OUTPUT
    # -------------------------------------------------

    output_file = FINAL_DIR / f"{uuid.uuid4().hex}.mp3"

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
            str(output_file),
        ],
        check=True,
    )

    print(f"✅ Blend created → {output_file}")

    # -------------------------------------------------
    # ✅ ✅ ✅ STEP 4 — UPLOAD TO S3 (CRITICAL ADDITION)
    # -------------------------------------------------

    try:
        s3_key = f"final_blends/{output_file.name}"

        print(f"☁️ Uploading to S3: {s3_key}")

        s3.upload_file(
            str(output_file),
            BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": "audio/mpeg"}
        )

        public_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        print(f"✅ Uploaded → {public_url}")

        return public_url   # ✅ IMPORTANT: return URL, not filename

    except Exception as e:
        print("🔥 S3 upload failed:", e)
        return None







