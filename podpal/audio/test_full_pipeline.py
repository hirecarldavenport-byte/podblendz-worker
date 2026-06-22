from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions

import uuid
import os
import asyncio
import hashlib
import json

import edge_tts
import azure.cognitiveservices.speech as speechsdk

from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment

# =========================
# ✅ ENVIRONMENT
# =========================

load_dotenv()

print("AZURE_SPEECH_KEY Exists:", bool(os.getenv("AZURE_SPEECH_KEY")))
print("AZURE_SPEECH_REGION:", os.getenv("AZURE_SPEECH_REGION"))

client = OpenAI()

# =========================
# ✅ QUALITY SETTINGS
# =========================

LEAD_PADDING_MS = 8000
TRAIL_PADDING_MS = 45000
MIN_CLIP_MS = 45000
MAX_CLIPS = 85

seen_texts = set()

# =========================
# ✅ DUPLICATE FILTER
# =========================

def is_duplicate(text):
    cleaned = " ".join(text.lower().split())

    key = hashlib.md5(
        cleaned.encode("utf-8")
    ).hexdigest()

    if key in seen_texts:
        return True

    seen_texts.add(key)
    return False


# =========================
# ✅ EDGE TTS
# =========================

async def tts_to_file(text, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-JennyNeural"
    )

    await communicate.save(output_path)


def fallback_tts(text, path):
    try:
        asyncio.run(
            tts_to_file(text, path)
        )

        return path

    except Exception as e:
        print(f"⚠️ Fallback TTS failed: {e}")
        return None


# =========================
# ✅ AZURE TTS
# =========================

def generate_tts(text, path):

    try:

        key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")

        print("🔍 Azure Key Loaded:", bool(key))
        print("🔍 Azure Region:", region)

        if not key or not region:
            return fallback_tts(text, path)

        speech_config = speechsdk.SpeechConfig(
            subscription=key,
            region=region
        )

        speech_config.speech_synthesis_voice_name = (
            "en-US-AriaNeural"
        )

        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=path
        )

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        result = synthesizer.speak_text_async(text).get()

        if (
            result
            and result.reason ==
            speechsdk.ResultReason.SynthesizingAudioCompleted
        ):
            return path

        print(
            f"⚠️ Azure failed: "
            f"{result.reason if result else 'Unknown'}"
        )

        return fallback_tts(text, path)

    except Exception as e:

        print(
            f"⚠️ Azure exception: {e}"
        )

        return fallback_tts(text, path)


# =========================
# ✅ SILENCE
# =========================

def create_silence(duration_ms, path):

    silence = AudioSegment.silent(
        duration=duration_ms
    )

    silence.export(
        path,
        format="mp3"
    )

    return path


# =========================
# ✅ INTRO
# =========================

def generate_podblendz_intro(query):

    try:

        prompt = f"""
You are the host of PodBlendz.

Create a natural podcast intro.

Topic:
{query}

Maximum 18 words.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = (
            response.choices[0]
            .message.content
        )

        return content.strip() if content else ""

    except Exception:

        return (
            f"From PodBlendz, "
            f"exploring {query}."
        )


# =========================
# ✅ SOURCE INTRO
# =========================

def generate_source_narration(
    source_path,
    text,
    query
):

    show_name = "this podcast"

    try:

        parts = source_path.split("/")

        if len(parts) > 2:
            show_name = (
                parts[-2]
                .replace("_", " ")
                .title()
            )

        prompt = f"""
Introduce this podcast clip.

Topic:
{query}

Podcast:
{show_name}

Maximum 16 words.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = (
            response.choices[0]
            .message.content
        )

        return content.strip() if content else ""

    except Exception:

        return (
            f"From {show_name}, "
            "here's another perspective."
        )


# =========================
# ✅ TEST AZURE TTS
# =========================

def test_azure_tts():

    print("\n🧪 Testing Azure TTS...\n")

    output = generate_tts(
        "Hello from PodBlendz.",
        "test_azure.mp3"
    )

    print("Result:", output)


# =========================
# ✅ MAIN PIPELINE
# =========================

def run_test(query="Dementia"):

    print("\n🚀 Running PodBlendz test...\n")

    blend = build_blend(query)

    print("\n===== BLEND TYPES =====")
    for step in blend:
        print(step.get("type"))

    if not blend:
        print("❌ No blend generated.")
        return

    print(
        f"✅ Blend steps: {len(blend)}"
    )

    speaker_steps = sum(
        1
        for step in blend
        if step.get("type") == "speaker"
    )

    print(
        f"✅ Speaker steps: {speaker_steps}"
    )

    blend_id = str(uuid.uuid4())

    os.makedirs("media", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    final_clips = []

    current_group = None
    last_audio = None

    # =========================
    # ✅ INTRO
    # =========================

    intro_text = generate_podblendz_intro(query)

    intro_audio = generate_tts(
        intro_text,
        f"media/{uuid.uuid4()}_intro.mp3"
    )

    if intro_audio:

        final_clips.append(
            ClipRange(
                intro_audio,
                0,
                60000
            )
        )

    silence = create_silence(
        700,
        f"media/{uuid.uuid4()}_silence.mp3"
    )

    final_clips.append(
        ClipRange(
            silence,
            0,
            700
        )
    )

    # =========================
    # ✅ BUILD TIMELINE
    # =========================

    for step in blend:

        if len(final_clips) >= MAX_CLIPS:
            break

        step_type = step.get("type")

        # =========================
        # ✅ SPEAKER CLIPS
        # =========================

        if step_type == "speaker":

            text = step.get("text", "")

            if not text:
                continue

            if is_duplicate(text):
                continue

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")

            if (
                not audio_file
                or start is None
                or end is None
            ):
                continue

            if audio_file != last_audio:

                if current_group:

                    final_clips.append(
                        ClipRange(**current_group)
                    )

                    current_group = None

                source_intro = generate_source_narration(
                    audio_file,
                    text,
                    query
                )

                intro_tts = generate_tts(
                    source_intro,
                    f"media/{uuid.uuid4()}_source.mp3"
                )

                if intro_tts:

                    final_clips.append(
                        ClipRange(
                            intro_tts,
                            0,
                            60000
                        )
                    )

            start_ms = max(
                0,
                int(start * 1000) - LEAD_PADDING_MS
            )

            end_ms = (
                int(end * 1000) + TRAIL_PADDING_MS
            )

            if end_ms - start_ms < MIN_CLIP_MS:

                end_ms = (
                    start_ms
                    + MIN_CLIP_MS
                )

            current_group = {
                "clip_id": audio_file,
                "start_ms": start_ms,
                "end_ms": end_ms
            }

            last_audio = audio_file

        # =========================
        # ✅ NARRATION
        # =========================

        elif step_type == "narration":

            text = step.get("text", "")

            if not text:
                continue

            tts_file = generate_tts(
                text,
                f"media/{uuid.uuid4()}_narration.mp3"
            )

            if tts_file:

                final_clips.append(
                    ClipRange(
                        tts_file,
                        0,
                        60000
                    )
                )

        # =========================
        # ✅ PAUSE
        # =========================

        elif step_type == "pause":

            duration = int(
                step.get("duration", 0.5)
                * 1000
            )

            pause = create_silence(
                duration,
                f"media/{uuid.uuid4()}_pause.mp3"
            )

            final_clips.append(
                ClipRange(
                    pause,
                    0,
                    duration
                )
            )

    if current_group:

        final_clips.append(
            ClipRange(**current_group)
        )


# =========================
# ✅ ENTRY POINT
# =========================

if __name__ == "__main__":
    run_test()