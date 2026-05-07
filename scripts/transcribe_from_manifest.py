"""
Fully hardened batch transcription driver using faster-whisper.

Updated:
- Supports BOTH S3-based and direct URL audio (source_url)
- Maintains resume-safe + ledger guarantees
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

WORKSPACE_ROOT = Path("/workspace/podblendz-backend")

DEFAULT_MANIFEST_PATH = WORKSPACE_ROOT / "episode_manifest_phase1.jsonl"
AUDIO_DIR = WORKSPACE_ROOT / "audio"
TRANSCRIPTS_DIR = WORKSPACE_ROOT / "transcripts"
LEDGER_PATH = WORKSPACE_ROOT / "transcription_ledger.jsonl"

WHISPER_MODEL = "medium"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
LANGUAGE = "en"

FFMPEG_PROBE_TIMEOUT_SEC = 45
MAX_ALLOWED_EPISODES = 750


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


def load_completed_episode_ids() -> set:
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

def load_manifest(manifest_path: Path) -> list:
    if not manifest_path.exists():
        raise RuntimeError(
            f"Manifest not found: {manifest_path}\n"
            "Generate the manifest before transcription."
        )

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = [json.loads(line) for line in f]

    if len(manifest) > MAX_ALLOWED_EPISODES:
        raise RuntimeError(
            f"Manifest contains {len(manifest)} episodes which exceeds "
            f"safety limit of {MAX_ALLOWED_EPISODES}"
        )

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

    raise RuntimeError("No audio URL found in manifest")


# =========================
# FFMPEG SAFETY GUARD
# =========================

def ffmpeg_probe_or_fail(audio_path: Path):
    subprocess.run(
        [
            "ffmpeg",
            "-v", "error",
            "-i", str(audio_path),
            "-f", "null",
            "-"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=FFMPEG_PROBE_TIMEOUT_SEC,
        check=True,
    )


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
    txt_out = TRANSCRIPTS_DIR / podcast_id / f"{episode_id}.txt"

    audio_path.parent.mkdir(parents=True, exist_ok=True)

    # =========================
    # DOWNLOAD
    # =========================

    if not audio_path.exists():
        if source_type == "s3":
            bucket, key = parse_s3_uri(audio_url)
            print("⬇️ Downloading from S3...", flush=True)
            s3.download_file(bucket, key, str(audio_path))

        elif source_type == "http":
            print("⬇️ Downloading from URL...", flush=True)
            download_http_audio(audio_url, audio_path)

    # =========================
    # VALIDATE
    # =========================

    ffmpeg_probe_or_fail(audio_path)

    # =========================
    # TRANSCRIBE
    # =========================

    segments, _ = model.transcribe(
        str(audio_path),
        language=LANGUAGE,
        vad_filter=True,
        beam_size=5,
    )

    transcript_segments = []
    plain_text = []

    for seg in segments:
        transcript_segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
        plain_text.append(seg.text.strip())

    json_out.parent.mkdir(parents=True, exist_ok=True)

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "episode_id": episode_id,
                "podcast_id": podcast_id,
                "model": WHISPER_MODEL,
                "language": LANGUAGE,
                "segments": transcript_segments,
            },
            f,
            indent=2,
        )

    with open(txt_out, "w", encoding="utf-8") as f:
        f.write("\n".join(plain_text))


# =========================
# MAIN
# =========================

def main():
    print(f"🧪 DEVICE={DEVICE}, COMPUTE_TYPE={COMPUTE_TYPE}", flush=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to episode manifest JSONL file"
    )
    args = parser.parse_args()

    print("🚀 Starting transcription driver", flush=True)

    completed = load_completed_episode_ids()
    manifest = load_manifest(args.manifest)

    print(f"✅ Episodes already completed: {len(completed)}", flush=True)
    print(f"📦 Episodes in manifest: {len(manifest)}", flush=True)

    model = WhisperModel(
        WHISPER_MODEL,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
    )

    for idx, episode in enumerate(
        tqdm(manifest, desc="Transcribing episodes"),
        start=1,
    ):
        episode_id = episode["episode_id"]
        podcast_id = episode["podcast_id"]

        if episode_id in completed:
            continue

        print(
            f"▶️ Starting episode {idx}/{len(manifest)}: "
            f"{podcast_id} / {episode_id}",
            flush=True,
        )

        append_ledger({
            "episode_id": episode_id,
            "podcast_id": podcast_id,
            "status": "started",
            "timestamp": time.time(),
        })

        try:
            transcribe_episode(model, episode)

            append_ledger({
                "episode_id": episode_id,
                "podcast_id": podcast_id,
                "status": "done",
                "timestamp": time.time(),
            })

        except Exception as e:
            append_ledger({
                "episode_id": episode_id,
                "podcast_id": podcast_id,
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": time.time(),
            })

            print(
                f"⚠️ Error on episode {episode_id}: {e}",
                flush=True,
            )


if __name__ == "__main__":
    main()




