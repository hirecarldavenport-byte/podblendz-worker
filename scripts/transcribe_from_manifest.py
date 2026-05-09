"""
Batch transcription driver using faster-whisper

✅ Fixes:
- indentation errors
- ffmpeg function bug
- supports s3 + http
- adds fast 5-minute transcription mode
"""

import json
import time
import traceback
import subprocess
import argparse
from pathlib import Path
from urllib.parse import urlparse

import boto3
import requests
from faster_whisper import WhisperModel
from tqdm import tqdm


# =========================
# CONFIGURATION
# =========================

WORKSPACE_ROOT = Path("./")

DEFAULT_MANIFEST_PATH = WORKSPACE_ROOT / "episode_manifest_test.jsonl"
AUDIO_DIR = WORKSPACE_ROOT / "audio"
TRANSCRIPTS_DIR = WORKSPACE_ROOT / "transcripts"
LEDGER_PATH = WORKSPACE_ROOT / "transcription_ledger.jsonl"

WHISPER_MODEL = "small"   # ✅ FAST MODEL
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
LANGUAGE = "en"

FFMPEG_PROBE_TIMEOUT_SEC = 45
MAX_ALLOWED_EPISODES = 50

FAST_MODE_SECONDS = 300  # ✅ 5-minute clip


# =========================
# AWS
# =========================

s3 = boto3.client("s3")


def parse_s3_uri(uri: str):
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


# =========================
# LEDGER
# =========================

def append_ledger(record: dict):
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_completed_episode_ids():
    completed = set()

    if LEDGER_PATH.exists():
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("status") == "done":
                    completed.add(rec["episode_id"])

    return completed


# =========================
# MANIFEST
# =========================

def load_manifest(manifest_path: Path):

    if not manifest_path.exists():
        raise RuntimeError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = [json.loads(line) for line in f]

    if len(manifest) > MAX_ALLOWED_EPISODES:
        raise RuntimeError("Too many episodes in manifest")

    return manifest


# =========================
# DOWNLOAD HELPERS
# =========================

def download_http_audio(url: str, output_path: Path):

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def resolve_audio_source(episode: dict):

    audio = episode.get("audio", {})

    if "s3_url" in audio:
        return "s3", audio["s3_url"]

    if "source_url" in audio:
        return "http", audio["source_url"]

    raise RuntimeError("No audio URL found")


# =========================
# FFMPEG
# =========================

def ffmpeg_probe_or_fail(audio_path: Path):

    short_path = audio_path.with_name("short_" + audio_path.name)

    subprocess.run(
        [
            "ffmpeg",
            "-v", "error",
            "-i", str(audio_path),
            "-ss", "600",
            "-t", "300",
            "-c", "copy",
            "-f", "null",
            str(short_path)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=FFMPEG_PROBE_TIMEOUT_SEC,
        check=True,
    )


def create_short_clip(original_path: Path):

    short_path = original_path.with_name("short_" + original_path.name)

    if short_path.exists():
        return short_path

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(original_path),
            "-t", str(FAST_MODE_SECONDS),
            "-c", "copy",
            str(short_path)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return short_path


# =========================
# TRANSCRIPTION
# =========================

def transcribe_episode(model: WhisperModel, episode: dict):

    episode_id = episode["episode_id"]
    podcast_id = episode["podcast_id"]

    source_type, audio_url = resolve_audio_source(episode)

    filename = Path(audio_url).name.split("?")[0]
    audio_path = AUDIO_DIR / podcast_id / filename

    json_out = TRANSCRIPTS_DIR / podcast_id / f"{episode_id}.json"

    audio_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------------------
    # DOWNLOAD
    # ---------------------

    if not audio_path.exists():

        if source_type == "s3":
            bucket, key = parse_s3_uri(audio_url)
            print("⬇️ Downloading S3...", flush=True)
            s3.download_file(bucket, key, str(audio_path))

        else:
            print("⬇️ Downloading URL...", flush=True)
            download_http_audio(audio_url, audio_path)

    # ---------------------
    # VALIDATE
    # ---------------------

    ffmpeg_probe_or_fail(audio_path)

    # ---------------------
    # FAST MODE CLIP
    # ---------------------

    short_audio = create_short_clip(audio_path)

    # ---------------------
    # TRANSCRIBE
    # ---------------------

    print("🧠 Transcribing...", flush=True)

    segments, _ = model.transcribe(
        str(short_audio),
        language=LANGUAGE,
        vad_filter=True,
        beam_size=5,
    )

    transcript_segments = []

    for seg in segments:
        transcript_segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    json_out.parent.mkdir(parents=True, exist_ok=True)

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "episode_id": episode_id,
                "podcast_id": podcast_id,
                "segments": transcript_segments,
            },
            f,
            indent=2,
        )

    print(f"✅ Saved: {json_out}")


# =========================
# MAIN
# =========================

def main():

    print(f"DEVICE={DEVICE}, MODEL={WHISPER_MODEL}", flush=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    args = parser.parse_args()

    completed = load_completed_episode_ids()
    manifest = load_manifest(args.manifest)

    print(f"✅ Completed: {len(completed)}")
    print(f"📦 Episodes: {len(manifest)}")

    model = WhisperModel(
        WHISPER_MODEL,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
    )

    for idx, episode in enumerate(tqdm(manifest), start=1):

        episode_id = episode["episode_id"]
        podcast_id = episode["podcast_id"]

        if episode_id in completed:
            continue

        print(f"\n▶️ {podcast_id} / {episode_id}")

        try:
            transcribe_episode(model, episode)

            append_ledger({
                "episode_id": episode_id,
                "status": "done",
                "timestamp": time.time(),
            })

        except Exception as e:

            append_ledger({
                "episode_id": episode_id,
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
            })

            print(f"⚠️ ERROR: {e}")


if __name__ == "__main__":
    main()
