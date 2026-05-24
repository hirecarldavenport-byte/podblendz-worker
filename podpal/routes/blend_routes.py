from typing import Optional
from fastapi import APIRouter
import uuid
import os
import boto3
from urllib.parse import urlparse

from podpal.semantic.blend_engine import build_blend

import azure.cognitiveservices.speech as speechsdk

print("🔥 FINAL BLEND ROUTES ACTIVE")

# -------------------------------------------------
# ✅ SAFE STITCH IMPORT
# -------------------------------------------------

stitch_blend = None
try:
    from podpal.audio.stitch import stitch_blendz
    stitch_blend = stitch_blendz
    print("✅ stitch loaded")
except Exception as e:
    print("⚠️ stitch import failed:", e)

# -------------------------------------------------
# ✅ ROUTER
# -------------------------------------------------

router = APIRouter()

# -------------------------------------------------
# ✅ S3 CLIENT
# -------------------------------------------------

s3 = boto3.client("s3")
BUCKET_NAME = "podblendz-episode-audio"

# -------------------------------------------------
# ✅ FETCH AUDIO
# -------------------------------------------------

def fetch_to_local(url: str):
    local_file = f"/tmp/{uuid.uuid4().hex}.mp3"

    try:
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")

        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)

        with open(local_file, "wb") as f:
            f.write(response["Body"].read())

        if os.path.getsize(local_file) < 2000:
            return None

        return local_file

    except Exception as e:
        print("❌ fetch error:", e)
        return None

# -------------------------------------------------
# ✅ AZURE TTS INTRO (FIXED)
# -------------------------------------------------

def generate_intro_audio(text: str):
    try:
        key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")

        if not key or not region:
            print("❌ Azure env missing")
            return None

        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

        output = f"/tmp/{uuid.uuid4().hex}.mp3"
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output)

        synth = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        # ✅ only ONE call (fixed)
        result = synth.speak_text_async(text).get()

        # ✅ FIX 1 (properly indented)
        if result and result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("✅ intro generated")
            return output
        else:
            print("❌ Azure TTS failed:", getattr(result, "reason", None))

    except Exception as e:
        print("❌ TTS error:", e)

    return None

# -------------------------------------------------
# ✅ SMOOTH CROSSFADE
# -------------------------------------------------

def apply_crossfade(inputs: list):
    if len(inputs) <= 1:
        return inputs

    import subprocess
    import imageio_ffmpeg

    output = f"/tmp/{uuid.uuid4().hex}.mp3"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    filter_complex = ""

    for i in range(len(inputs) - 1):
        if i == 0:
            filter_complex += f"[0:a][1:a]acrossfade=d=1[a1];"
        else:
            filter_complex += f"[a{i}][{i+1}:a]acrossfade=d=1[a{i+1}];"

    last = f"a{len(inputs)-1}"

    cmd = [ffmpeg, "-y"]

    for inp in inputs:
        cmd += ["-i", inp]

    cmd += [
        "-filter_complex", filter_complex[:-1],
        "-map", f"[{last}]",
        output
    ]

    subprocess.run(cmd, check=True)

    return [output]

# -------------------------------------------------
# ✅ /blend ENDPOINT
# -------------------------------------------------

@router.get("/blend")
def get_blend(minutes: Optional[int] = 5, theme_index: Optional[int] = None):

    print("\n🎯 /blend hit")

    try:
        sequence = build_blend(theme_index=theme_index)

        if not sequence:
            return {
                "mode": "semantic_blend",
                "theme": None,
                "steps": 0,
                "segments": [],
                "final_audio": None,
            }

        # ✅ theme
        theme = None
        for step in sequence:
            if step.get("type") == "intro":
                theme = step.get("text")
                break

        # ✅ intro audio
        intro_audio = generate_intro_audio(theme) if theme else None

        # ✅ clips
        clips = [
            step["content"]
            for step in sequence
            if step.get("type") == "clip"
        ]

        audio_files = []

        if intro_audio:
            audio_files.append(intro_audio)

        import subprocess
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        for clip in clips:
            url = clip.get("audio_path")
            if not url:
                continue

            local = fetch_to_local(url)
            if not local:
                continue

            start = clip.get("start", 0)
            duration = min(20, clip.get("end", start + 20) - start)

            out = f"/tmp/{uuid.uuid4().hex}.mp3"

            try:
                subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-i", local,
                        "-ss", str(start),
                        "-t", str(duration),
                        "-vn",
                        "-acodec", "libmp3lame",
                        out,
                    ],
                    check=True
                )

                if os.path.exists(out) and os.path.getsize(out) > 2000:
                    audio_files.append(out)

            except Exception as e:
                print("❌ trim failed:", e)

        if len(audio_files) < 2:
            return {
                "mode": "semantic_blend",
                "theme": theme,
                "steps": len(clips),
                "segments": clips,
                "final_audio": None,
            }

        print("🎧 applying crossfade...")
        audio_files = apply_crossfade(audio_files)

        print("🎧 stitching...")

        # ✅ FIX 2 (safe call)
        final_audio = None
        if stitch_blend:
            try:
                final_audio = stitch_blend(audio_files, minutes or 1)
            except Exception as e:
                print("🔥 stitch error:", e)
        else:
            print("⚠️ stitch not available")

        return {
            "mode": "semantic_blend",
            "theme": theme,
            "steps": len(clips),
            "segments": clips,
            "final_audio": final_audio,
        }

    except Exception as e:
        print("❌ blend error:", e)

        return {
            "mode": "semantic_blend",
            "theme": None,
            "steps": 0,
            "segments": [],
            "final_audio": None,
            "error": str(e),
        }