import os
from pathlib import Path
import subprocess
import uuid
from typing import List
import imageio_ffmpeg

# -------------------------------------------------
# ✅ SINGLE PATH SYSTEM (CRITICAL)
# -------------------------------------------------

AUDIO_DIR = Path("/app/audio")
TEMP_DIR = AUDIO_DIR / "temp"
FINAL_DIR = AUDIO_DIR / "final"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

print("✅ AUDIO DIR:", AUDIO_DIR)
print("✅ FINAL DIR:", FINAL_DIR)

# -------------------------------------------------
# ✅ CONFIG
# -------------------------------------------------

MIN_CLIPS_REQUIRED = 2
CLIP_DURATION = 6
TARGET_TOTAL_SEGMENTS = 2

# -------------------------------------------------
# ✅ PROCESS AUDIO (FIXED)
# -------------------------------------------------

def process_audio(input_file: str) -> str:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    # ✅ CRITICAL: validate input file
    if not os.path.exists(input_file) or os.path.getsize(input_file) < 2000:
        raise RuntimeError("Invalid or corrupt audio file")

    print(f"🎧 Processing: {input_file}")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", input_file,                 # ✅ moved BEFORE -ss
            "-ss", "0",
            "-t", str(CLIP_DURATION),
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "128k",
            str(output_file),
        ],
        check=True,
    )

    # ✅ Validate output
    if not output_file.exists() or output_file.stat().st_size < 2000:
        raise RuntimeError("Processed file invalid")

    return str(output_file)

# -------------------------------------------------
# ✅ VALIDATE INPUT
# -------------------------------------------------

def validate_sequence(audio_files: List[str]) -> None:
    if len(audio_files) < MIN_CLIPS_REQUIRED:
        raise RuntimeError(f"❌ Not enough clips ({len(audio_files)})")

# -------------------------------------------------
# ✅ CONCAT FILE
# -------------------------------------------------

def create_concat_file(audio_files: List[str], concat_file: Path):
    lines = [f"file '{Path(a).resolve().as_posix()}'" for a in audio_files]
    concat_file.write_text("\n".join(lines), encoding="utf-8")

# -------------------------------------------------
# ✅ MAIN STITCH (HARDENED)
# -------------------------------------------------

def stitch_blendz(audio_files: List[str], target_minutes: int = 5) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if not audio_files:
        raise RuntimeError("❌ No audio files provided")

    print("\n🎯 Building PodBlend...")

    validate_sequence(audio_files)

    processed_files = []
    i = 0
    iterations = 0
    max_iterations = 4

    print("\n🔄 Expanding sequence...")

    while (
        len(processed_files) < TARGET_TOTAL_SEGMENTS
        and iterations < max_iterations
    ):
        iterations += 1

        audio = audio_files[i % len(audio_files)]

        try:
            processed = process_audio(audio)
            processed_files.append(processed)

        except Exception as e:
            print(f"⚠️ Skipping bad file: {audio} → {e}")

        i += 1

    # ✅ FINAL SAFETY CHECK
    if len(processed_files) < 1:
        raise RuntimeError("❌ No valid audio clips to stitch")

    # -------------------------------------------------
    # ✅ CONCAT + OUTPUT
    # -------------------------------------------------

    concat_file = TEMP_DIR / f"concat_{uuid.uuid4().hex}.txt"
    create_concat_file(processed_files, concat_file)

    output_file = FINAL_DIR / f"{uuid.uuid4().hex}.mp3"

    print("\n🎧 Rendering final audio...")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame",
            "-q:a", "3",
            str(output_file),
        ],
        check=True,
    )

    print(f"\n✅ Blend created → {output_file}")

    return output_file.name







