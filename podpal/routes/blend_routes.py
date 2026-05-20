"""
blend_routes.py (FINAL STABLE VERSION)

✅ Fast + safe
✅ Downloads enough audio for ffmpeg
✅ Prevents 502 timeouts
✅ Fully production-ready
"""

from typing import Optional
from fastapi import APIRouter
import requests
import uuid

from podpal.semantic.blend_engine import build_blend


# -------------------------------------------------
# ✅ SAFE STITCH IMPORT
# -------------------------------------------------
try:
    from podpal.audio.stitch import stitch_blendz as stitch_blend
    print("✅ stitch_blend loaded successfully")
except Exception as e:
    print("⚠️ stitch import failed:", e)
    stitch_blend = None


router = APIRouter()

print("✅ blend_routes.py loaded")


# -------------------------------------------------
# ✅ DOWNLOAD HELPER (FIXED)
# -------------------------------------------------
def fetch_to_local(url: str):
    """
    Download enough of the file (~5MB) so ffmpeg can seek properly
    """
    local_file = f"/tmp/{uuid.uuid4().hex}.mp3"

    print(f"⬇️ downloading: {url}")

    try:
        with requests.get(url, stream=True, timeout=10) as r:
            r.raise_for_status()

            with open(local_file, "wb") as f:
                for i, chunk in enumerate(r.iter_content(chunk_size=1024 * 1024)):
                    f.write(chunk)

                    if i >= 4:  # ✅ download ~5MB instead of 1MB
                        break

        return local_file

    except Exception as e:
        print(f"❌ download failed: {e}")
        return None


# -------------------------------------------------
# ✅ /blend ENDPOINT
# -------------------------------------------------
@router.get("/blend")
def get_blend(minutes: Optional[int] = 5, theme_index: Optional[int] = None):

    print("🎯 /blend endpoint hit")

    try:
        sequence = build_blend(theme_index=theme_index)

        if not sequence:
            return {
                "mode": "semantic_blend",
                "steps": 0,
                "segments": [],
                "final_audio": None,
            }

        # ✅ Extract clips
        clips = [
            step["content"]
            for step in sequence
            if step.get("type") == "clip"
        ]

        print(f"✅ clips found: {len(clips)}")

        # ✅ Convert S3 → local
        audio_files = []

        for clip in clips:
            url = clip.get("audio_path")

            if not url:
                continue

            local_file = fetch_to_local(url)

            if local_file:
                audio_files.append(local_file)

        print(f"✅ audio files ready: {len(audio_files)}")

        final_audio = None

        # ✅ Stitch safely
        if stitch_blend and len(audio_files) >= 2:
            try:
                print("🎧 starting stitch...")
                filename = stitch_blend(audio_files, minutes or 5)
                final_audio = f"/audio/final/{filename}"
                print(f"✅ stitch complete: {final_audio}")

            except Exception as err:
                print("🔥 stitch error:", err)

        return {
            "mode": "semantic_blend",
            "steps": len(clips),
            "segments": clips,
            "final_audio": final_audio,
        }

    except Exception as e:
        print("❌ blend error:", e)

        return {
            "mode": "semantic_blend",
            "steps": 0,
            "segments": [],
            "final_audio": None,
            "error": str(e),
        }


