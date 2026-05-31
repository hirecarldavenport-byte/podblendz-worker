from __future__ import annotations

import os
import uuid
import html
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk


# -------------------------------------------------
# ✅ LOAD ENV
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")


# -------------------------------------------------
# ✅ OUTPUT DIR
# -------------------------------------------------
TTS_DIR = BASE_DIR / "audio" / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ TEXT HELPERS
# -------------------------------------------------
def clean_text(text: str) -> str:
    return " ".join(text.split())


def safe_ssml(text: str) -> str:
    return html.escape(text)


# -------------------------------------------------
# ✅ MAIN FUNCTION
# -------------------------------------------------
def generate_dual_voice_audio(
    blend,
    narrator_voice="en-US-JennyNeural",
    speaker_voice="en-US-GuyNeural",
    filename_prefix="blend"
) -> str:

    print("🔐 AZURE KEY LOADED:", bool(AZURE_KEY))
    print("🌍 AZURE REGION:", AZURE_REGION)

    if not AZURE_KEY or not AZURE_REGION:
        raise RuntimeError("❌ Missing Azure Speech credentials")

    if not blend:
        raise RuntimeError("❌ Blend is empty — cannot generate audio")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]

    output_path = TTS_DIR / f"{filename_prefix}_{timestamp}_{uid}.wav"

    print(f"🎙 Generating dual-voice audio → {output_path}")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_KEY,
        region=AZURE_REGION
    )

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=str(output_path)
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # -------------------------------------------------
    # ✅ BUILD FIXED SSML
    # -------------------------------------------------
    ssml_parts = [
        '<speak xmlns="http://www.w3.org/2001/10/synthesis" '
        'version="1.0" xml:lang="en-US">'
    ]

    current_voice = None
    buffer = []

    def flush():
        """Write buffered text inside a voice tag"""
        if not buffer or not current_voice:
            return

        combined = " ".join(buffer)
        ssml_parts.append(
            f'<voice name="{current_voice}">{combined}</voice>'
        )

        buffer.clear()

    for step in blend:

        if step["type"] == "narration":
            if current_voice != narrator_voice:
                flush()
                current_voice = narrator_voice

            buffer.append(safe_ssml(clean_text(step["text"])))

        elif step["type"] == "speaker":
            if current_voice != speaker_voice:
                flush()
                current_voice = speaker_voice

            buffer.append(safe_ssml(clean_text(step["text"])))

        elif step["type"] == "pause":
            # ✅ pause INSIDE voice (append to buffer)
            duration_ms = int(step.get("duration", 0.4) * 1000)
            buffer.append(f'<break time="{duration_ms}ms"/>')

    # ✅ final flush
    flush()

    ssml_parts.append("</speak>")

    ssml = "\n".join(ssml_parts)

    # Uncomment if you want to debug XML
    # print(ssml)

    # -------------------------------------------------
    # ✅ SYNTHESIS
    # -------------------------------------------------
    result = synthesizer.speak_ssml_async(ssml).get()

    if result is None:
        raise RuntimeError("❌ Azure returned no result")

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details

            print("❌ Azure TTS canceled")

            if cancellation:
                print("🔹 Reason:", cancellation.reason)
                print("🔹 Error details:", cancellation.error_details)
            else:
                print("⚠️ No cancellation details")

        else:
            print("❌ Unexpected result:", result.reason)

        raise RuntimeError("❌ Dual voice TTS failed")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("❌ Audio file invalid")

    print(f"✅ Dual voice audio created → {output_path}")

    return str(output_path)





