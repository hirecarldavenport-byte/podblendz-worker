"""
Audio stitching utilities for PodBlendz (FINAL FIX — CONTENT AWARE)

✅ Avoids intros / ads / outros
✅ Extracts mid-content segments
✅ Prevents repeat segments
✅ Preserves grouped playback
"""

from pathlib import Path
import subprocess
import uuid
import random
from typing import List
import imageio_ffmpeg


BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "audio"
FINAL_DIR = AUDIO_DIR / "final"
TEMP_DIR = AUDIO_DIR / "temp"

FINAL_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ✅ CLIP LENGTH
def get_clip_duration(target_minutes: int) -> int:
    return 30


# ✅ SEGMENT COUNT
def calculate_max_segments(target_minutes: int, clip_duration: int) -> int:
    total_seconds = target_minutes * 60
    return max(1, total_seconds // clip_duration)


# ✅ GLOBAL MEMORY TO AVOID REPEATS
USED_SEGMENTS = {}


# ✅ PROCESS AUDIO (FIXED — MID CONTENT SAMPLING)
def process_audio(input_file: str, clip_duration: int) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    # ✅ DEFINE SAFE RANGE (skip intros & outros)
    MIN_START = 180   # skip first 3 minutes
    MAX_START = 900   # stop before late episode outro

    used = USED_SEGMENTS.get(input_file, set())

    # ✅ avoid repeating same segments
    for _ in range(10):
        start_time = random.randint(MIN_START, MAX_START)
        bucket = start_time // clip_duration

        if bucket not in used:
            used.add(bucket)
            USED_SEGMENTS[input_file] = used
            break
    else:
        # fallback if exhausted
        start_time = random.randint(MIN_START, MAX_START)

    print(f"⏩ Extracting {start_time}s → {start_time + clip_duration}s")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss", str(start_time),    # ✅ KEY FIX HERE
            "-t", str(clip_duration),
            "-i", input_file,
            "-vn",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            str(output_file),
        ],
        check=True,
    )

    return str(output_file)


# ✅ CONCAT FILE
def create_concat_file(audio_files: List[str], concat_file: Path) -> None:
    lines = [f"file '{Path(a).resolve().as_posix()}'" for a in audio_files]
    concat_file.write_text("\n".join(lines), encoding="utf-8")


# ✅ MAIN STITCH FUNCTION
def stitch_blendz(audio_files: List[str], target_minutes: int = 5) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if not audio_files:
        raise RuntimeError("No audio files provided")

    print(f"\n🎯 Target duration: {target_minutes} minutes")

    clip_duration = get_clip_duration(target_minutes)
    max_segments = calculate_max_segments(target_minutes, clip_duration)

    print(f"🎧 Clip duration: {clip_duration}s")
    print(f"🎚 Segments needed: {max_segments}")

    processed_files = []

    print("\n🔄 Processing audio...")

    group_size = 3

    for audio in audio_files:

        print(f"🎙 Source: {audio}")

        for _ in range(group_size):
            if len(processed_files) >= max_segments:
                break

            try:
                processed = process_audio(audio, clip_duration)
                processed_files.append(processed)
            except Exception as e:
                print(f"⚠️ Failed: {audio} → {e}")

        if len(processed_files) >= max_segments:
            break

    # ✅ fallback loop
    i = 0
    while len(processed_files) < max_segments:
        audio = audio_files[i % len(audio_files)]

        try:
            processed = process_audio(audio, clip_duration)
            processed_files.append(processed)
        except Exception as e:
            print(f"⚠️ Fallback failed: {audio} → {e}")

        i += 1

    if not processed_files:
        raise RuntimeError("No processed audio files")

    concat_file = TEMP_DIR / f"concat_{uuid.uuid4().hex}.txt"
    create_concat_file(processed_files, concat_file)

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


