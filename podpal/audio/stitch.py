"""
Audio stitching utilities for PodBlendz.

Purpose:
- Normalize narration + podcast clips
- Concatenate into a single audio file
- Produce stable, high-quality podcast output

Implementation:
- Uses FFmpeg (via imageio_ffmpeg)
- Normalization ensures compatibility between sources
"""

from pathlib import Path
import subprocess
import uuid
from typing import List

import imageio_ffmpeg


# -------------------------------------------------
# ✅ Directory setup
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

AUDIO_DIR = BASE_DIR / "audio"
FINAL_DIR = AUDIO_DIR / "final"
TEMP_DIR = AUDIO_DIR / "temp"

FINAL_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ Normalize audio (CRITICAL)
# -------------------------------------------------
def normalize_audio(input_file: str) -> str:
    """
    Convert audio into a consistent format:
    - mp3
    - 44100 Hz
    - stereo

    Returns:
        Path to normalized file
    """

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    output_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", input_file,
            "-ar", "44100",  # sample rate
            "-ac", "2",      # stereo
            "-b:a", "192k",  # quality
            str(output_file),
        ],
        check=True,
    )

    return str(output_file)


# -------------------------------------------------
# ✅ Create concat file
# -------------------------------------------------
def create_concat_file(audio_files: List[str], concat_file: str | Path) -> None:
    """
    Create FFmpeg concat input file.
    """

    lines: List[str] = []

    for audio in audio_files:
        path = Path(audio).resolve()
        lines.append(f"file '{path.as_posix()}'")

    Path(concat_file).write_text("\n".join(lines), encoding="utf-8")


# -------------------------------------------------
# ✅ Main stitching function
# -------------------------------------------------
def stitch_blendz(audio_files: List[str]) -> str:
    """
    Stitch narration and clips into one final podcast.

    Expected ordering:
        [narration1, clip1, narration2, clip2, ...]

    Returns:
        Final filename (string)
    """

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if not audio_files:
        raise RuntimeError("No audio files provided for stitching")

    print("\n🔄 Normalizing audio...")

    normalized_files: List[str] = []

    for audio in audio_files:
        try:
            normalized = normalize_audio(audio)
            normalized_files.append(normalized)
        except Exception as e:
            print(f"⚠️ Failed to normalize: {audio} → {e}")

    if not normalized_files:
        raise RuntimeError("No valid audio after normalization")

    # -------------------------------------------------
    # Create concat file
    # -------------------------------------------------
    concat_file = TEMP_DIR / f"concat_{uuid.uuid4().hex}.txt"
    create_concat_file(normalized_files, str(concat_file))

    # -------------------------------------------------
    # Output file
    # -------------------------------------------------
    output_file = FINAL_DIR / f"{uuid.uuid4().hex}.mp3"

    print("\n🎧 Stitching final audio...")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame",  # re-encode safely
            "-q:a", "2",           # high quality
            str(output_file),
        ],
        check=True,
    )

    print(f"\n✅ Final podcast created → {output_file}")

    return output_file.name