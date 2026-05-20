"""
PodBlendz Stitch Engine (FAST + STABLE VERSION)

✅ Works in constrained environments (Render)
✅ Uses short clips (fast response)
✅ Safe loop limits (no hanging)
✅ Clean audio processing
"""

from pathlib import Path
import subprocess
import uuid
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
# ✅ CONFIG (FAST MODE)
# -------------------------------------------------
MIN_CLIPS_REQUIRED = 2
CLIP_DURATION = 6            # VERY SHORT (fast)
TARGET_TOTAL_SEGMENTS = 2    # VERY SMALL LOOP

# -------------------------------------------------
# ✅ AUDIO TYPE DETECTION
# -------------------------------------------------
def detect_audio_type(path: str) -> str:
    if "/tts/" in path:
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
            "-ss", "0",  # skip intro
            "-t", str(CLIP_DURATION),
            "-i", input_file,
            "-af",
            # ✅ FIXED fade timing (matches 6s clip)
            "afade=t=in:st=0:d=1,"
            "afade=t=out:st=4:d=1,"
            "loudnorm=I=-16:LRA=11:TP=-1.5",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "128k",
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
        raise RuntimeError(f"❌ Not enough clips ({len(audio_files)})")


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

    validate_sequence(audio_files)

    processed_files = []
    i = 0
    iterations = 0
    max_iterations = 4  # ✅ SAFE LIMIT

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
            print(f"⚠️ Failed: {audio} → {e}")

        i += 1

    if not processed_files:
        raise RuntimeError("❌ No audio processed")

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
            "-q:a", "3",
            str(output_file),
        ],
        check=True,
    )

    print(f"\n✅ Blend created → {output_file}")

    return output_file.name





