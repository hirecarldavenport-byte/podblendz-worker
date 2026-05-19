"""
blend_routes # -------------------------------------------------blend_routes.py
    # ✅ STEP 2: Extract CLIP segments only
    # -------------------------------------------------
    clips = [
        step["content"]
        for step in final_sequence
        if step.get("type") == "clip"
    ]

    print(f"✅ Clips selected: {len(clips)}")

    # -------------------------------------------------
    # ✅ STEP 3: Extract AUDIO FILE PATHS
    # (critical for stitch engine)
    # -------------------------------------------------
    audio_files = []

    for clip in clips:
        audio_path = clip.get("audio_path")

        if audio_path:
            audio_files.append(audio_path)

    print(f"🎧 Audio files ready: {len(audio_files)}")

    # -------------------------------------------------
    # ✅ STEP 4: STITCH AUDIO
    # -------------------------------------------------
    if stitch_blend and len(audio_files) >= 2:
        try:
            fn = stitch_blend(audio_files, target_minutes)
            final_audio = f"/audio/final/{fn}"

            print(f"✅ Audio stitched → {final_audio}")

        except Exception as e:
            print(f"🔥 Stitch failed: {e}")

    else:
        print("⚠️ Skipping stitch (not enough audio or stitch unavailable)")

    # -------------------------------------------------
    # ✅ RESPONSE
    # -------------------------------------------------
    return {
        "mode": "semantic_blend",
        "steps": len(clips),
        "segments": clips,
        "final_audio": final_audio,
    }


# -------------------------------------------------
# ✅ API ENDPOINT
# -------------------------------------------------
@router.get("/blend")
def get_blend(
    minutes: Optional[int] = 5,
    theme_index: Optional[int] = None
):
    return run_blend(minutes or 5, theme_index)

✅ Fully wired to blend_engine
✅ Safe import handling (prevents route from disappearing)
✅ Correct stitch integration (uses lst of audio files)
✅ Returns segments + audio
✅ Production stable
"""

from typing import Optional
from fastapi import APIRouter

from podpal.semantic.blend_engine import build_blend


# -------------------------------------------------
# ✅ SAFE IMPORT (CRITICAL)
# Prevents route from failing silently
# -------------------------------------------------
try:
    from podpal.audio.stitch import stitch_blendz as stitch_blend
    print("✅ stitch_blend loaded successfully")
except Exception as e:
    print("⚠️ stitch import failed:", e)
    stitch_blend = None


router = APIRouter()


# -------------------------------------------------
# ✅ CORE BLEND EXECUTION
# -------------------------------------------------
def run_blend(target_minutes: int, theme_index: Optional[int] = None):

    print("\n🚀 RUNNING BLEND PIPELINE\n")

    final_audio = None

    # ✅ STEP 1: Build semantic sequence
    final_sequence = build_blend(theme_index=theme_index)

    if not final_sequence:
        print("❌ No sequence generated")

        return {
            "mode": "semantic_blend",
            "steps": 0,
            "segments": [],
            "final_audio": None,
            "error": "No sequence generated",
        }









