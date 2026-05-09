"""
Audio ingestion utilities.

Responsibilities:
- Download episode audio to a temporary file
- Compute audio duration (via ffprobe if available)
- Upload audio to S3
- Enforce a per-podcaster ingestion cap (early-stage safety)
"""

import os
import tempfile
import subprocess
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Dict

import boto3
import requests

from config.settings import AWS_REGION, EPISODE_AUDIO_BUCKET


# -------------------------------------------------
# INGESTION SAFETY LIMIT
# -------------------------------------------------

MAX_EPISODES_PER_PODCAST = 50

# In-memory counter: podcast_id -> count
_podcast_ingest_counts: Dict[str, int] = {}


@dataclass
class AudioIngestResult:
    s3_key: str
    duration_seconds: int


# -------------------------------------------------
# PUBLIC ENTRY POINT
# -------------------------------------------------

def ingest_episode_audio(
    master_topic: str,
    podcast,
    rss_item,
) -> AudioIngestResult:
    podcast_id = str(podcast.id)

    count = _podcast_ingest_counts.get(podcast_id, 0)
    if count >= MAX_EPISODES_PER_PODCAST:
        raise RuntimeError(
            f"Per-run cap reached ({MAX_EPISODES_PER_PODCAST}) "
            f"for podcast '{podcast_id}'."
        )

    audio_url = rss_item.enclosure_url
    episode_id = str(rss_item.guid)

    print(f"[AUDIO] Downloading episode audio: {audio_url}")

    with _download_to_tempfile(audio_url) as tmp_path:
        duration = _compute_audio_duration(tmp_path)

        s3_key = _upload_to_s3(
            file_path=tmp_path,
            master_topic=master_topic,
            podcast_id=podcast_id,
            episode_id=episode_id,
        )

    # Increment only after successful upload
    _podcast_ingest_counts[podcast_id] = count + 1

    return AudioIngestResult(
        s3_key=s3_key,
        duration_seconds=duration,
    )


# -------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------

@contextmanager
def _download_to_tempfile(url: str):
    """
    Stream-download audio to a Windows-safe temporary file.

    - Strips query parameters from URLs
    - Uses safe extensions only
    - Gracefully handles Ctrl+C during streaming
    """
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[-1].lower()

    if ext not in (".mp3", ".m4a", ".wav", ".aac", ".ogg"):
        ext = ".mp3"

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=ext,
    )

    try:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmp.write(chunk)

        tmp.flush()
        tmp.close()
        yield tmp.name

    finally:
        try:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
        except PermissionError:
            # Windows can briefly lock temp files if Ctrl+C interrupts streaming.
            print(f"[WARN] Temp file locked, cleanup deferred: {tmp.name}")


def _compute_audio_duration(path: str) -> int:
    """
    Compute duration via ffprobe.

    Returns 0 if:
    - file missing
    - ffprobe unavailable
    - any probing error occurs

    MUST NOT crash ingestion.
    """
    if not os.path.exists(path):
        print(f"[WARN] Audio file missing for duration check: {path}")
        return 0

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        print("[WARN] ffprobe not found on PATH; duration set to 0")
        return 0

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return int(float(result.stdout.strip()))

    except Exception as e:
        print(f"[WARN] ffprobe failed, duration set to 0: {e}")
        return 0


def _upload_to_s3(
    file_path: str,
    master_topic: str,
    podcast_id: str,
    episode_id: str,
) -> str:
    s3 = boto3.client("s3", region_name=AWS_REGION)

    ext = os.path.splitext(file_path)[-1]
    s3_key = f"{master_topic}/{podcast_id}/{episode_id}{ext}"

    print(
        f"[AUDIO] Uploading episode audio to "
        f"s3://{EPISODE_AUDIO_BUCKET}/{s3_key}"
    )

    s3.upload_file(
        Filename=file_path,
        Bucket=EPISODE_AUDIO_BUCKET,
        Key=s3_key,
    )

    return s3_key
