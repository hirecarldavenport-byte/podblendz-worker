# podpal/audio/ingest.py

import requests
from pathlib import Path
import uuid
from typing import Optional

# -------------------------------------------------
# Base directory for audio storage
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "audio"

RAW_DIR = AUDIO_DIR / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# Download episode audio
# -------------------------------------------------

def download_episode_audio(audio_url: str) -> Optional[str]:
    """
    Downloads audio from a remote URL and saves locally.

    Returns:
        filename (str)
    """

    # ✅ Unique filename (avoid collisions)
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = RAW_DIR / filename

    try:
        response = requests.get(audio_url, stream=True, timeout=15)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filename

    except Exception as e:
        print(f"⚠️ Failed to download audio: {e}")
        return None
