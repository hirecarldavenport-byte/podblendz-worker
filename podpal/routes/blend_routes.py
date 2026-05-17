"""
blend_routes.py

✅ Thin API layer for semantic blending
✅ Uses blend_engine for sequence generation
✅ Uses clipper for real audio segments
✅ Handles TTS + stitching
"""

from fastapi import APIRouter
from typing import Optional, List

from podpal.semantic.blend_engine import build_blend
from podpal.audio.stitch import stitch_blendz
from podpal.audio.tts import generate_audio
from podpal.audio.clipper import extract_audio_clip

router = APIRouter()


# -------------------------------------------------
# ✅ SAFE TTS
# -------------------------------------------------
def safe_generate_audio(text: str, label: str):
    try:
        return generate_audio(text, label)
    except Exception as e:
        print(f"⚠️ TTS failed ({label}): {e}")
        return None


# -------------------------------------------------
# ✅ CORE BLEND FUNCTION
# -------------------------------------------------
def run_blend(target_minutes: int, theme_index: Optional[int] = None):

    print("\n🎧 RUNNING SEMANTIC BLEND\n")

    sequence = build_blend(theme_index)

    final_sequence: List[str] = []

    for step in sequence:

        # ✅ INTRO
        if step.get("type") == "intro":
            audio = safe_generate_audio(step.get("text", ""), "intro")
            if audio:
                final_sequence.append(audio)

        # ✅ TRANSITION
        elif step.get("type") == "transition":
            audio = safe_generate_audio(step.get("text", ""), "transition")
            if audio:
                final_sequence.append(audio)

        # ✅ REAL AUDIO CLIPS
        elif step.get("type") == "clip":

            content = step.get("content", {})

            audio_path = content.get("audio_path")
            start = content.get("start")
            end = content.get("end")

            if audio_path and start is not None and end is not None:
                try:
                    clip_file = extract_audio_clip(audio_path, start, end)
                    final_sequence.append(clip_file)
                except Exception as e:
                    print(f"⚠️ Clip extraction failed: {e}")
            else:
                print("⚠️ Missing clip metadata — skipping")

    print(f"✅ Final sequence length: {len(final_sequence)}")

    # -------------------------------------------------
    # ✅ STITCH FINAL AUDIO
    # -------------------------------------------------
    final_audio = None

    try:
        if not final_sequence:
            raise ValueError("No audio segments generated")

        fn = stitch_blendz(final_sequence, target_minutes)
        final_audio = f"/audio/final/{fn}"

    except Exception as e:
        print(f"🔥 Stitch failed: {e}")

    return {
        "mode": "semantic_blend",
        "steps": len(final_sequence),
        "final_audio": final_audio
    }


# -------------------------------------------------
# ✅ API ENDPOINT
# -------------------------------------------------
@router.get("/blend")
def get_blend(minutes: Optional[int] = 5, theme_index: Optional[int] = None):
    return run_blend(minutes or 5, theme_index)






