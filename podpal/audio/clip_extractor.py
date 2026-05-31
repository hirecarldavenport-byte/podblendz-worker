from pydub import AudioSegment
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_SOURCE_DIR = BASE_DIR / "audio" / "raw"


def extract_clip(audio_file: str, start: float, end: float) -> AudioSegment:
    """
    Extract real audio segment from source file
    """

    full_path = AUDIO_SOURCE_DIR / audio_file

    if not full_path.exists():
        raise FileNotFoundError(f"Missing audio file: {full_path}")

    audio = AudioSegment.from_file(full_path)

    start_ms = int(start * 1000)
    end_ms = int(end * 1000)

    return audio[start_ms:end_ms]
