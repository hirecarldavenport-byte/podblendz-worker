from typing import Optional 

from fastapi import APIRouter
import requests
import uuid

from podpal.semantic.blend_engine import build_blend

# -------------------------------------------------
# ✅ SAFE STITCH IMPORT (FIXED)
# -------------------------------------------------
stitch_blend = None

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
# ✅ DOWNLOAD HELPER
# -------------------------------------------------
def fetch_to_local(url: str):
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
# ✅ /blend ENDPOINT (DEBUG VERSION)
# -------------------------------------------------
@router.get("/blend")
def get_blend(minutes: Optional[int] = 5, theme_index: Optional[int] = None):

    print("\n🎯 /blend endpoint hit")

    try:
        # ✅ STEP 1: BUILD SEQUENCE
        sequence = build_blend(theme_index=theme_index)

        print("DEBUG sequence:", sequence)

        if not sequence:
            print("❌ No sequence built")
            return {
                "mode": "semantic_blend",
                "steps": 0,
                "segments": [],
                "final_audio": None,
            }

        # ✅ STEP 2: EXTRACT CLIPS
        clips = [
            step["content"]
            for step in sequence
            if step.get("type") == "clip"
        ]

        print(f"✅ clips found: {len(clips)}")

        # ✅ STEP 3: DOWNLOAD + TRIM
        audio_files = []

        for idx, clip in enumerate(clips):
            print(f"\n--- Processing clip {idx} ---")

            url = clip.get("audio_path")

            if not url:
                print("❌ Missing audio_path")
                continue

            local_file = fetch_to_local(url)

            if not local_file:
                print("❌ Failed to download file")
                continue

            start = clip.get("start", 0)
            end = clip.get("end", start + 10)
            duration = end - start

            print(f"DEBUG start={start}, end={end}, duration={duration}")

            trimmed_file = f"/tmp/{uuid.uuid4().hex}.mp3"

            try:
                import subprocess
                import imageio_ffmpeg

                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

                print("🎧 Running ffmpeg trim...")

                subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-loglevel", "error",
                        "-ss", str(start),
                        "-t", str(min(duration, 6)),
                        "-i", local_file,
                        "-vn",
                        "-acodec", "libmp3lame",
                        trimmed_file,
                    ],
                    check=True,
                )

                print(f"✅ trimmed file created: {trimmed_file}")

                audio_files.append(trimmed_file)

            except Exception as e:
                print(f"❌ trimming failed: {e}")

                # ✅ FALLBACK (IMPORTANT)
                print("⚠️ Using original file as fallback")
                audio_files.append(local_file)

        # ✅ DEBUG OUTPUT
        print("\n==============================")
        print("DEBUG FINAL AUDIO FILES:")
        for f in audio_files:
            print(f)
        print(f"TOTAL FILES: {len(audio_files)}")
        print("==============================\n")

        final_audio = None

        # ✅ STEP 4: STITCH
        print("DEBUG stitch_blend exists:", stitch_blend is not None)
        print("DEBUG len(audio_files):", len(audio_files))

        if stitch_blend and len(audio_files) >= 2:
            try:
                print("🎧 Starting stitch...")

                filename = stitch_blend(audio_files, minutes or 5)

                print("✅ stitch returned filename:", filename)

                final_audio = f"/audio/final/{filename}"

                print("✅ FINAL AUDIO PATH:", final_audio)

            except Exception as err:
                print("🔥 stitch error:", err)

        else:
            print("⚠️ Not enough files or stitch not available")

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






