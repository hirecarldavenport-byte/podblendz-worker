"""
Audio stitching utilities for PodBlendz (AI HOSTED EXPERIENCE VERSION)

✅ Role-aware audio handling
✅ Intro ALWAYS preserved
✅ Narration & transitions flow naturally
✅ Smooth fades + spacing + leveling
✅ No duplication or segmentation of TTS
✅ Designed for AI-hosted podcast structure
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


# ✅ allow room for narration segments
def calculate_max_segments(target_minutes: int, clip_duration: int) -> int:
    total_seconds = target_minutes * 60
    return max(3, total_seconds // clip_duration + 3)


USED_SEGMENTS = {}


# ✅ DETECT AUDIO ROLE
def detect_audio_type(path: str) -> str:
    if "/tts/" in path:
        name = Path(path).name.lower()

        if "intro" in name:
            return "intro"
        if "outro" in name:
            return "outro"
        if "transition" in name:
            return "transition"
        return "narration"

    return "clip"


# ✅ PROCESS AUDIO BY ROLE
def process_audio(input_file: str, clip_duration: int) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    audio_type = detect_audio_type(input_file)

    print(f"🎧 Processing ({audio_type}): {input_file}")

    # -------------------------------------------------
    # ✅ TTS HANDLING (intro / narration / transition / outro)
    # -------------------------------------------------
    if audio_type in ["intro", "narration", "transition", "outro"]:

        fade_in = "0.4"
        fade_out = "0.6"

        if audio_type == "intro":
            fade_out = "1.2"   # longer intro fade

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i", input_file,
                "-af",
                f"afade=t=in:ss=0:d={fade_in},"
                f"afade=t=out:st=3:d={fade_out},"
                "loudnorm=I=-16:LRA=7:TP=-1.5,"
                "apad=pad_dur=0.4",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "192k",
                str(output_file),
            ],
            check=True,
        )

        return str(output_file)

    # -------------------------------------------------
    # ✅ PODCAST CLIPS (CONTENT)
    # -------------------------------------------------
    MIN_START = 180
    MAX_START = 900

    used = USED_SEGMENTS.get(input_file, set())

    for _ in range(10):
        start_time = random.randint(MIN_START, MAX_START)
        bucket = start_time // clip_duration

        if bucket not in used:
            used.add(bucket)
            USED_SEGMENTS[input_file] = used
            break
    else:
        start_time = random.randint(MIN_START, MAX_START)

    print(f"⏩ Extracting {start_time}s → {start_time + clip_duration}s")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss", str(start_time),
            "-t", str(clip_duration),
            "-i", input_file,
            "-vn",
            "-af",
            "afade=t=in:ss=0:d=1,"
            "afade=t=out:st=27:d=1,"
            "loudnorm=I=-16:LRA=11:TP=-1.5,"
            "apad=pad_dur=0.3",
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
    print(f"🎚 Max segments: {max_segments}")

    processed_files = []
    print("\n🔄 Processing audio sequence...")

    last_clip_source = None

    for audio in audio_files:

        try:
            audio_type = detect_audio_type(audio)

            # ✅ process
            processed = process_audio(audio, clip_duration)

            # ✅ avoid repeating same content source twice
            if audio_type == "clip":
                if last_clip_source == audio:
                    print("⚠️ Skipping duplicate clip source")
                    continue
                last_clip_source = audio

            processed_files.append(processed)

            if len(processed_files) >= max_segments:
                break

        except Exception as e:
            print(f"⚠️ Failed: {audio} → {e}")

    if not processed_files:
        raise RuntimeError("No processed audio files")

    # -------------------------------------------------
    # ✅ FINAL CONCAT
    # -------------------------------------------------
    concat_file = TEMP_DIR / f"concat_{uuid.uuid4().hex}.txt"
    create_concat_file(processed_files, concat_file)

    output_file = FINAL_DIR / f"{uuid.uuid4().hex}.mp3"

    print("\n🎧 Rendering final podcast...")

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




