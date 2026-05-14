# podpal/audio/ingest.py

import requests
from pathlib import Path
import uuid
from typing import Optional
import time

# -------------------------------------------------
# ✅ Base directory for audio storage
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "audio"
RAW_DIR = AUDIO_DIR / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ Download episode audio (FIXED + STABLE)
# -------------------------------------------------

def download_episode_audio(audio_url: str) -> Optional[str]:
    """
    Downloads audio from a remote URL and saves locally.

    ✅ Now allows normal podcast sizes (NO 50MB restriction)
    ✅ Still protected against broken downloads
    ✅ Uses retries + chunk streaming

    Returns:
        filename (str) OR None if download fails
    """

    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = RAW_DIR / filename

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }

    max_retries = 2

    for attempt in range(max_retries):
        try:
            print(f"\n⬇️ Attempt {attempt+1} downloading audio:")
            print(audio_url)

            response = requests.get(
                audio_url,
                headers=headers,
                stream=True,
                timeout=20,
                allow_redirects=True,
            )

            response.raise_for_status()

            # ✅ LOG size (DO NOT BLOCK it)
            content_length = response.headers.get("content-length")

            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                print(f"📦 File size: {size_mb:.1f} MB")

            # ✅ Write file (streaming)
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # ✅ Validate file exists + not empty
            if not filepath.exists() or filepath.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty")

            print(f"✅ Audio downloaded → {filepath}")

            return filename

        except Exception as e:
            print(f"⚠️ Download failed (attempt {attempt+1}): {e}")
            time.sleep(1)

    # ✅ Cleanup if failed
    if filepath.exists():
        try:
            filepath.unlink()
        except Exception:
            pass

    print("❌ Failed to download audio after retries")

    return None
