"""
PodBlendz Stitch Engine (FINAL CLEAN VERSION)

✅ Works with local audio files only
✅ Designed for Render / production
✅ Smooth fades + normalization
"""

from pathlib import Path
import subprocess
import uuid
import random
from typing import List
import imageio_ffmpeg


# -------------------------------------------------
# ✅ PATHS
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "audio"
FINAL_DIR = AUDIO_DIR / "final"
TEMP_DIR = AUDIO_DIR / "temp"

FINAL_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ CONFIG
# -------------------------------------------------
MIN_CLIPS_REQUIRED = 2   # lowered for flexibility
CLIP_DURATION = 30
TARGET_TOTAL_SEGMENTS = 12  # ~5 min

USED_SEGMENTS = {}


# -------------------------------------------------
# ✅ TYPE DETECTION
# -------------------------------------------------
def detect_audio_type(path: str) -> str:
    if "/tts/" in path:
        name = Path(path).name.lower()

        if "intro" in name:
            return "intro"
        if "transition" in name:
            return "transition"
        if "outro" in name:
            return "outro"

        return "narration"

    return "clip"


# -------------------------------------------------
# ✅ PROCESS AUDIO
# -------------------------------------------------
def process_audio(input_file: str) -> str:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    print(f"🎧 Processing: {input_file}")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss", "10",               # safe start
            "-t", str(CLIP_DURATION),
            "-i", input_file,
            "-af",
            "afade=t=in:st=0:d=1,"
            "afade=t=out:st=27:d=1,"
            "loudnorm=I=-16:LRA=11:TP=-1.5",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            str(output_file),
        ],
        check=True,
    )

    return str(output_file)


# -------------------------------------------------
# ✅ VALIDATION
# -------------------------------------------------
def validate_sequence(audio_files: List[str]) -> None:

    if len(audio_files) < MIN_CLIPS_REQUIRED:
        raise RuntimeError(
            f"❌ Not enough clips ({len(audio_files)})"
        )


# -------------------------------------------------
# ✅ CONCAT FILE
# -------------------------------------------------
def create_concat_file(audio_files: List[str], concat_file: Path):
    lines = [f"file '{Path(a).resolve().as_posix()}'" for a in audio_files]
    concat_file.write_text("\n".join(lines), encoding="utf-8")


# -------------------------------------------------
# ✅ MAIN STITCH
# -------------------------------------------------
def stitch_blendz(audio_files: List[str], target_minutes: int = 5) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if not audio_files:
        raise RuntimeError("❌ No audio files provided")

    print("\n🎯 Building PodBlend...")

    # ✅ Ensure minimum clips
    validate_sequence(audio_files)

    processed_files = []
    last_clip_source = None
    i = 0

    print("\n🔄 Expanding sequence...")

    # ✅ Expand until full duration
    while len(processed_files) < TARGET_TOTAL_SEGMENTS:

        audio = audio_files[i % len(audio_files)]

        try:
            audio_type = detect_audio_type(audio)

            if audio_type == "clip":
                if audio == last_clip_source:
                    i += 1
                    continue
                last_clip_source = audio

            processed = process_audio(audio)
            processed_files.append(processed)

        except Exception as e:
            print(f"⚠️ Failed: {audio} → {e}")

        i += 1

    # -------------------------------------------------
    # ✅ FINAL CONCAT
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
            "-q:a", "2",
            str(output_file),
        ],
        check=True,
    )

    print(f"\n✅ Blend created → {output_file}")

    return output_file.name





