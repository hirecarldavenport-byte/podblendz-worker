import subprocess
from pathlib import Path
import uuid


def extract_audio_clip(input_path: str, start: float, end: float) -> str:
    output_file = Path("audio/temp") / f"{uuid.uuid4().hex}.mp3"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    duration = max(0.1, end - start)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ss", str(start),
        "-t", str(duration),
        "-acodec", "copy",
        str(output_file),
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return str(output_file)