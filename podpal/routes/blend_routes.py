"""
blend_routes.py production-safe routeblend_routes.py
✅ Properly connected to blend_engine
✅ Safe stitch integration
"""

from typing import Optional
from fastapi import APIRouter

from podpal.semantic.blend_engine import build_blend

# -------------------------------------------------
# ✅ SAFE STITCH IMPORT (prevents route failure)
# -------------------------------------------------
try:
    from podpal.audio.stitch import stitch_blendz as stitch_blend
    print("✅ stitch_blend loaded successfully")
except Exception as e:
    print("⚠️ stitch import failed:", e)
    stitch_blend = None


# ✅ MUST exist BEFORE decorator
router = APIRouter()

print("✅ blend_routes.py loaded")


# -------------------------------------------------
# ✅ ENDPOINT
# -------------------------------------------------
@router.get("/blend")
def get_blend(
    minutes: Optional[int] = 5,
    theme_index: Optional[int] = None
):
    print("🎯 /blend endpoint hit")

    sequence = build_blend(theme_index=theme_index)

    if not sequence:
        return {
            "mode": "semantic_blend",
            "steps": 0,
            "segments": [],
            "final_audio": None,
        }

    # ✅ Extract clip segments
    clips = [
        step["content"]
        for step in sequence
        if step.get("type") == "clip"
    ]

    # ✅ Extract audio paths
    audio_files = [
        clip.get("audio_path")
        for clip in clips
        if clip.get("audio_path")
    ]

    final_audio = None

    # ✅ Stitch audio if possible
    if stitch_blend and len(audio_files) >= 2:
        try:
            filename = stitch_blend(audio_files, minutes or 5)
            final_audio = f"/audio/final/{filename}"
        except Exception as err:
            print("🔥 stitch error:", err)

    return {
        "mode": "semantic_blend",
        "steps": len(clips),
        "segments": clips,
        "final_audio": final_audio,
    }

