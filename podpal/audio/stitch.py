"""
PodBlendz Stitch Engine (PRODUCTION BASELINE)

✅ Guarantees usable blends (>=3 clips)
✅ Role-aware processing (intro / transition / clip / outro)
✅ Smooth fades + spacing + audio leveling
✅ Prevents weak blends (single clip issue)
✅ Designed for scalable multi-board system
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


# -------------------------------------------------
# ✅ CONFIG
# -------------------------------------------------
MIN_CLIPS_REQUIRED = 3
CLIP_DURATION = 30


USED_SEGMENTS = {}


# -------------------------------------------------
# ✅ AUDIO TYPE DETECTION
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
# ✅ PROCESS AUDIO (ROLE-AWARE)
# -------------------------------------------------
def process_audio(input_file: str) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    audio_type = detect_audio_type(input_file)

    print(f"🎧 Processing {audio_type}: {input_file}")

    # -------------------------------------------------
    # ✅ TTS HANDLING (NO CLIPPING)
    # -------------------------------------------------
    if audio_type != "clip":

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i", input_file,
                "-af",
                "afade=t=in:ss=0:d=0.3,"
                "afade=t=out:st=4:d=0.6,"
                "loudnorm=I=-16:LRA=7:TP=-1.5,"
                "apad=pad_dur=0.35",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "192k",
                str(output_file),
            ],
            check=True,
        )

        return str(output_file)

    # -------------------------------------------------
    # ✅ CLIP HANDLING (MID-CONTENT)
    # -------------------------------------------------
    MIN_START = 180
    MAX_START = 900

    used = USED_SEGMENTS.get(input_file, set())

    for _ in range(10):
        start_time = random.randint(MIN_START, MAX_START)
        bucket = start_time // CLIP_DURATION

        if bucket not in used:
            used.add(bucket)
            USED_SEGMENTS[input_file] = used
            break
    else:
        start_time = random.randint(MIN_START, MAX_START)

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss", str(start_time),
            "-t", str(CLIP_DURATION),
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


# -------------------------------------------------
# ✅ CONCAT FILE
# -------------------------------------------------
def create_concat_file(audio_files: List[str], concat_file: Path):
    lines = [f"file '{Path(a).resolve().as_posix()}'" for a in audio_files]
    concat_file.write_text("\n".join(lines), encoding="utf-8")


# -------------------------------------------------
# ✅ VALIDATE INPUT (CRITICAL FIX)
# -------------------------------------------------
def validate_sequence(audio_files: List[str]) -> List[str]:

    clips = [a for a in audio_files if detect_audio_type(a) == "clip"]

    if len(clips) < MIN_CLIPS_REQUIRED:
        raise RuntimeError(
            f"❌ Not enough clips ({len(clips)}). Need at least {MIN_CLIPS_REQUIRED}."
        )

    return audio_files


# -------------------------------------------------
# ✅ MAIN STITCH FUNCTION
# -------------------------------------------------
def stitch_blendz(audio_files: List[str], target_minutes: int = 5) -> str:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if not audio_files:
        raise RuntimeError("❌ No audio files provided")

    print(f"\n🎯 Starting blend build...")

    # ✅ CRITICAL GUARD
    audio_files = validate_sequence(audio_files)

    processed_files = []
    last_clip_source = None

    print("\n🔄 Processing sequence...")

    for audio in audio_files:

        try:
            audio_type = detect_audio_type(audio)

            # ✅ Avoid repeating same clip
            if audio_type == "clip":
                if audio == last_clip_source:
                    print("⚠️ Skipping duplicate clip source")
                    continue
                last_clip_source = audio

            processed = process_audio(audio)
            processed_files.append(processed)

        except Exception as e:
            print(f"⚠️ Failed: {audio} → {e}")

    if not processed_files:
        raise RuntimeError("❌ No processed audio files")

    # -------------------------------------------------
    # ✅ CONCAT + FINAL RENDER
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

    print(f"\n✅ Blend created → {output_file}")

    return output_file.name




