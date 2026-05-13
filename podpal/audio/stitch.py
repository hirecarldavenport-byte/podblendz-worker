"""
Audio stitching utilities for PodBlendz (UPGRADED)

✅ Normalize narration + podcast clips
✅ Trim clips dynamically based on target duration
✅ Control total runtime (5, 10, 25 min)
✅ Produce balanced audio experience
"""

from pathlib import Path
import subprocess
import uuid
from typing import List

import imageio_ffmpeg


# -------------------------------------------------
# ✅ DIRECTORY SETUP
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "audio"
FINAL_DIR = AUDIO_DIR / "final"
TEMP_DIR = AUDIO_DIR / "temp"

FINAL_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ CLIP DURATION BASED ON FINAL LENGTH
# -------------------------------------------------
def get_clip_duration(target_minutes: int) -> int:
    if target_minutes <= 5:
        return 12
    elif target_minutes <= 10:
        return 15
    elif target_minutes <= 25:
        return 20
    else:
        return 25


# -------------------------------------------------
# ✅ MAX SEGMENTS CALCULATOR
# -------------------------------------------------
def calculate_max_segments(target_minutes: int, clip_duration: int) -> int:
    total_seconds = target_minutes * 60

    # narration ~ same length as clip
    segment_duration = clip_duration * 2

    return max(1, total_seconds // segment_duration)


# -------------------------------------------------
# ✅ NORMALIZE + TRIM AUDIO
# -------------------------------------------------
def process_audio(input_file: str, clip_duration: int) -> str:
    """
    Normalize audio and trim clip length
    """

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    subprocess.run(
        [
            ffmpeg,
            "-y",

            # ✅ TRIM
            "-ss", "0",
            "-t", str(clip_duration),

            "-i", input_file,
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            str(output_file),
        ],
        check=True,
    )

    return str(output_file)


# -------------------------------------------------
# ✅ CREATE CONCAT FILE
# -------------------------------------------------
def create_concat_file(audio_files: List[str], concat_file: Path) -> None:
    lines = []

    for audio in audio_files:
        path = Path(audio).resolve()
        lines.append(f"file '{path.as_posix()}'")

    concat_file.write_text("\n".join(lines), encoding="utf-8")


# -------------------------------------------------
# ✅ MAIN STITCH FUNCTION (UPDATED)
# -------------------------------------------------
def stitch_blendz(audio_files: List[str], target_minutes: int = 5) -> str:
    """
    Stitch narration + clips into final output

    NEW:
    ✅ Controls duration based on target_minutes
    ✅ Trims clips intelligently
    ✅ Limits number of segments
    """

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if not audio_files:
        raise RuntimeError("No audio files provided")

    print(f"\n🎯 Target duration: {target_minutes} minutes")

    # ✅ Determine clip length
    clip_duration = get_clip_duration(target_minutes)
    max_segments = calculate_max_segments(target_minutes, clip_duration)

    print(f"🎧 Clip duration: {clip_duration}s")
    print(f"🎚 Max segments: {max_segments}")

    processed_files = []

    count = 0

    print("\n🔄 Processing audio...")

    for i, audio in enumerate(audio_files):

        # ✅ LIMIT TOTAL SEGMENTS
        if count >= max_segments * 2:
            break

        try:
            processed = process_audio(audio, clip_duration)
            processed_files.append(processed)
            count += 1

        except Exception as e:
            print(f"⚠️ Failed processing: {audio} → {e}")

    if not processed_files:
        raise RuntimeError("No audio files after processing")

    # -------------------------------------------------
    # concat file
    # -------------------------------------------------
    concat_file = TEMP_DIR / f"concat_{uuid.uuid4().hex}.txt"
    create_concat_file(processed_files, concat_file)

    # -------------------------------------------------
    # output
    # -------------------------------------------------
    output_file = FINAL_DIR / f"{uuid.uuid4().hex}.mp3"

    print("\n🎧 Stitching final output...")

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

    print(f"\n✅ Final podcast created → {output_file}")

    return output_file.name
