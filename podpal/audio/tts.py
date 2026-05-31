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
# ✅ TEXT CLEANING
# -------------------------------------------------
def clean_text(text: str) -> str:
    """Normalize spacing for smoother speech"""
    return " ".join(text.split())


def add_pauses(text: str) -> str:
    """Light pacing improvement without SSML"""
    text = text.replace(". ", ". ... ")
    text = text.replace("? ", "? ... ")
    text = text.replace("! ", "! ... ")
    return text


# -------------------------------------------------
# ✅ NARRATOR TTS (CORE FUNCTION)
# -------------------------------------------------
def generate_audio(
    text: str,
    voice: str = "en-US-JennyNeural",
    filename_prefix: str = "narrator"
) -> str:
    """
    Generate narrator-only audio.

    Used by:
    ✅ audio_builder (hybrid system)
    ✅ narration layers

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
    # ✅ OUTPUT FILE
    # -------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]

    output_path = TTS_DIR / f"{filename_prefix}_{timestamp}_{uid}.wav"

    print(f"🎙 Generating narrator audio → {output_path}")

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
    # ✅ SYNTHESIZE (NO SSML = STABLE)
    # -------------------------
    result = synthesizer.speak_text_async(text).get()

    # -------------------------
    # ✅ ERROR HANDLING
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

        raise RuntimeError("❌ Narrator TTS failed")

    # -------------------------
    # ✅ VALIDATE FILE
    # -------------------------
    if not output_path.exists():
        raise RuntimeError("❌ Audio file was not created")

    if output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("❌ Audio file is empty")

    print(f"✅ Narrator audio created → {output_path}")

    return str(output_path)






