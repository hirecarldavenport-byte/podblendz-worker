# podpal/audio/tts.py

import os
import uuid
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk


# -----------------------------
# ✅ LOAD ENV
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

KEY = os.getenv("AZURE_SPEECH_KEY")
REGION = os.getenv("AZURE_SPEECH_REGION")


# -----------------------------
# ✅ OUTPUT DIR
# -----------------------------
TTS_DIR = BASE_DIR / "audio" / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# ✅ MAIN FUNCTION
# -----------------------------
def generate_audio(
    text: str,
    voice: str = "en-US-JennyNeural",
    filename_prefix: str = "blend",
):
    print("🔐 KEY loaded:", bool(KEY))
    print("🌍 REGION:", REGION)

    if not KEY or not REGION:
        raise RuntimeError("Missing Azure credentials")

    # file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]

    output = TTS_DIR / f"{filename_prefix}_{timestamp}_{uid}.wav"

    print(f"🎙 Generating → {output}")

    # config
    speech_config = speechsdk.SpeechConfig(
        subscription=KEY,
        region=REGION
    )

    speech_config.speech_synthesis_voice_name = voice

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=str(output)
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # ✅ IMPORTANT: plain text (NO SSML)
    result = synthesizer.speak_text_async(text).get()
    if result is None:
       raise RuntimeError("No result returned") 

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError("TTS failed")

    print(f"✅ Audio created → {output}")

    return str(output)


