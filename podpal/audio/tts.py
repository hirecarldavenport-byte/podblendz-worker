from __future__ import annotations

import os
import uuid
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
# ✅ OUTPUT DIRECTORY
# -------------------------------------------------
TTS_DIR = BASE_DIR / "audio" / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ TEXT UTILITIES
# -------------------------------------------------
def clean_text(text: str) -> str:
    """Normalize whitespace."""
    return " ".join(text.split())


def add_pauses(text: str) -> str:
    """
    Add natural pauses without SSML.
    Uses ellipses, which Azure handles well.
    """
    return text.replace(". ", ". ... ")


# -------------------------------------------------
# ✅ MAIN FUNCTION
# -------------------------------------------------
def generate_audio(
    text: str,
    voice: str = "en-US-JennyNeural",
    filename_prefix: str = "blend",
) -> str:
    """
    Generate audio from text using Azure TTS (safe mode).

    Returns:
        Path to WAV file
    """

    print("🔐 AZURE KEY LOADED:", bool(AZURE_KEY))
    print("🌍 AZURE REGION:", AZURE_REGION)

    if not AZURE_KEY or not AZURE_REGION:
        raise RuntimeError("❌ Missing Azure Speech credentials")

    # -------------------------
    # ✅ PREP TEXT
    # -------------------------
    text = clean_text(text)
    text = add_pauses(text)

    # -------------------------
    # ✅ BUILD OUTPUT PATH
    # -------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]

    output_path = TTS_DIR / f"{filename_prefix}_{timestamp}_{uid}.wav"

    print(f"🎙 Generating audio → {output_path}")

    # -------------------------
    # ✅ AZURE CONFIG
    # -------------------------
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_KEY,
        region=AZURE_REGION
    )

    speech_config.speech_synthesis_voice_name = voice

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=str(output_path)
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # -------------------------
    # ✅ SYNTHESIS (NO SSML)
    # -------------------------
    result = synthesizer.speak_text_async(text).get()

    if result is None:
        raise RuntimeError("No result returned")

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError("❌ Azure TTS generation failed")

    # -------------------------
    # ✅ VALIDATE OUTPUT
    # -------------------------
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("❌ Audio file was not created correctly")

    print(f"✅ Audio created → {output_path}")

    return str(output_path)



