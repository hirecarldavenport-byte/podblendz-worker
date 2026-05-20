from typing import Optional 
from fastapi import APIRouter
import requests
import uuid

from podpal.semantic.blend_engine import build_blend

# -------------------------------------------------
# ✅ SAFE STITCH IMPORT (FIXED)
# -------------------------------------------------
stitch_blend = None  # ✅ always defined

try:
    from podpal.audio.stitch import stitch_blendz
    stitch_blend = stitch_blendz
    print("✅ stitch_blend loaded successfully")
except Exception as e:
    print("⚠️ stitch import failed:", e)


# -------------------------------------------------
# ✅ ROUTER
# -------------------------------------------------
router = APIRouter()

print("✅ blend_routes.py loaded")


# -------------------------------------------------
# ✅ DOWNLOAD HELPER (RELIABLE VERSION)
# -------------------------------------------------
def fetch_to_local(url: str):
    """
    Download full file for ffmpeg reliability
    """
    local_file = f"/tmp/{uuid.uuid4().hex}.mp3"

    print(f"⬇️ downloading: {url}")

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            print(f"❌ bad status: {r.status_code}")
            return None

        with open(local_file, "wb") as f:
            f.write(r.content)

        print(f"✅ saved: {local_file}")

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
        # ✅ STEP 1: Get semantic sequence
        sequence = build_blend(theme_index=theme_index)

        if not sequence:
            return {
                "mode": "semantic_blend",
                "steps": 0,
                "segments": [],
                "final_audio": None,
            }

        # ✅ STEP 2: Extract clips
        clips = [
            step["content"]
            for step in sequence
            if step.get("type") == "clip"
        ]

        print(f"✅ clips found: {len(clips)}")

        # ✅ STEP 3: Download audio locally
        audio_files = []

        for clip in clips:
            url = clip.get("audio_path")

            if not url:
                continue

            local_file = fetch_to_local(url)

            if local_file:
                audio_files.append(local_file)

        print("DEBUG audio_files:", audio_files)
        print("DEBUG audio_files count:", len(audio_files))

        final_audio = None

        # ✅ STEP 4: Stitch audio
        if stitch_blend and len(audio_files) >= 2:
            try:
                print("🎧 starting stitch...")
                print("DEBUG ready to stitch:", len(audio_files))

                filename = stitch_blend(audio_files, minutes or 5)

                print("DEBUG filename:", filename)

                final_audio = f"/audio/final/{filename}"

                print(f"✅ stitch complete: {final_audio}")

            except Exception as err:
                print("🔥 stitch error:", err)

        else:
            print("⚠️ Not enough audio files to stitch")

        # ✅ STEP 5: Return response
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



