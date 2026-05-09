"""
Audio Ingestion Module

✅ Downloads episode audio
✅ Saves locally (no AWS required)
✅ Structured for future S3 re-enable
"""

import os
import tempfile
import requests
import shutil
from pathlib import Path
from urllib.parse import urlparse


# =========================
# CONFIG
# =========================

BASE_AUDIO_DIR = Path("local_audio")


# =========================
# CORE FUNCTION
# =========================

def ingest_episode_audio(master_topic: str, podcast, rss_item):
    """
    Download audio from RSS item and store locally.
    """

    audio_url = extract_audio_url(rss_item)

    if not audio_url:
        print("[WARN] No audio URL found. Skipping.")
        return None

    episode_id = generate_episode_id(audio_url)

    print(f"[AUDIO] Downloading episode audio: {audio_url}")

    tmp_path = download_to_tempfile(audio_url)

    if not tmp_path:
        print("[ERROR] Failed to download audio.")
        return None

    local_path = save_locally(
        file_path=tmp_path,
        master_topic=master_topic,
        podcast_id=podcast.id,
        episode_id=episode_id,
    )

    return {
        "episode_id": episode_id,
        "local_path": local_path,
        "source_url": audio_url,
    }


# =========================
# HELPERS
# =========================

def extract_audio_url(rss_item):
    """
    Extract audio URL from RSS item.
    """

    enclosures = getattr(rss_item, "enclosures", None)

    if isinstance(enclosures, list) and len(enclosures) > 0:
        enclosure = enclosures[0]

        if isinstance(enclosure, dict):
            url = enclosure.get("href")

            if isinstance(url, str):
                return url

    return None


def generate_episode_id(url: str) -> str:
    """
    Create a stable ID from URL.
    """
    import hashlib
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def download_to_tempfile(url: str):
    """
    Download audio file into a temp file.
    """

    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)

                return tmp.name

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None


def save_locally(file_path: str, master_topic: str, podcast_id: str, episode_id: str):
    """
    Save downloaded file into local structured directory.
    """

    target_dir = BASE_AUDIO_DIR / master_topic / podcast_id
    target_dir.mkdir(parents=True, exist_ok=True)

    dest_path = target_dir / f"{episode_id}.mp3"

    shutil.copy(file_path, dest_path)

    print(f"[AUDIO] Saved locally: {dest_path}")

    return str(dest_path)

