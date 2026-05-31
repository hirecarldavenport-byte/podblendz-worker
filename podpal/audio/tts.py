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
    """Normalize spacing"""
    return " ".join(text.split())


def safe_ssml(text: str) -> str:
    """Escape characters that break XML"""
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
    """
    Generate dual-voice audio:

    🎙 Narrator = guided storytelling
    🎧 Speaker = segment voice
    """

    print("🔐 AZURE KEY LOADED:", bool(AZURE_KEY))
    print("🌍 AZURE REGION:", AZURE_REGION)

    if not AZURE_KEY or not AZURE_REGION:
        raise RuntimeError("❌ Missing Azure Speech credentials")

    # -------------------------
    # ✅ FILE NAME
    # -------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]

    output_path = TTS_DIR / f"{filename_prefix}_{timestamp}_{uid}.wav"

    print(f"🎙 Generating dual-voice audio → {output_path}")

    # -------------------------
    # ✅ AZURE CONFIG
    # -------------------------
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

    # -------------------------
    # ✅ BUILD SAFE SSML
    # -------------------------
    ssml_parts = [
        '<speak xmlns="http://www.w3.org/2001/10/synthesis" '
        'version="1.0" xml:lang="en-US">'
    ]

    for step in blend:

        if step["type"] == "narration":
            text = safe_ssml(clean_text(step["text"]))

            ssml_parts.append(
                f'<voice name="{narrator_voice}">{text}</voice>'
            )

        elif step["type"] == "speaker":
            text = safe_ssml(clean_text(step["text"]))

            ssml_parts.append(
                f'<voice name="{speaker_voice}">{text}</voice>'
            )

        elif step["type"] == "pause":
            duration_ms = int(step.get("duration", 0.4) * 1000)

            ssml_parts.append(
                f'<break time="{duration_ms}ms"/>'
            )

    ssml_parts.append("</speak>")

    ssml = "\n".join(ssml_parts)

    # OPTIONAL DEBUG
    # print("----- SSML START -----")
    # print(ssml)
    # print("----- SSML END -----")

    # -------------------------
    # ✅ SYNTHESIZE
    # -------------------------
    result = synthesizer.speak_ssml_async(ssml).get()

    # -------------------------
    # ✅ ERROR HANDLING (CLEAN)
    # -------------------------
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
                print("⚠️ No cancellation details available")

        else:
            print("❌ Unexpected result:", result.reason)

        raise RuntimeError("❌ Dual voice TTS failed")

    # -------------------------
    # ✅ VALIDATION
    # -------------------------
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("❌ Audio file was not created correctly")

    print(f"✅ Dual voice audio created → {output_path}")

    return str(output_path)





