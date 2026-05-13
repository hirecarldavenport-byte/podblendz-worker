# podpal/audio/tts.py

from __future__ import annotations

import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk


# -------------------------------------------------
# ✅ FORCE LOAD ENV FROM PROJECT ROOT
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_path = BASE_DIR / ".env"
load_dotenv(env_path)

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")


# -------------------------------------------------
# ✅ DIRECTORIES
# -------------------------------------------------
TTS_DIR = BASE_DIR / "audio" / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ✅ MAIN TTS FUNCTION
# -------------------------------------------------
def generate_audio(
    text: str,
    voice: str = "en-US-JennyNeural",
    filename_prefix: str = "blend",
) -> str:
    """
    Generate TTS audio using Azure Speech Service.

    Returns:
        Absolute path to MP3 file.
    """

    # ✅ HARD DEBUG (remove later if you want)
    print(f"🔐 AZURE KEY LOADED: {bool(AZURE_SPEECH_KEY)}")
    print(f"🌍 AZURE REGION: {AZURE_SPEECH_REGION}")

    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise RuntimeError("❌ Azure Speech is not configured (missing env vars)")

    # -------------------------------------------------
    # ✅ FILENAME
    # -------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{filename_prefix}_{timestamp}_{unique_id}.mp3"

    output_path = TTS_DIR / filename

    print(f"🔊 Azure TTS generating → {output_path}")

    try:
        # -------------------------------------------------
        # ✅ CONFIGURE SPEECH
        # -------------------------------------------------
        speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION
        )

        speech_config.speech_synthesis_voice_name = voice

        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=str(output_path)
        )

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        # -------------------------------------------------
        # ✅ SYNTHESIS
        # -------------------------------------------------
        result: Optional[speechsdk.SpeechSynthesisResult] = (
            synthesizer.speak_text_async(text).get()
        )

        if not result:
            raise RuntimeError("Azure TTS returned no result")

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"⚠️ Azure TTS unexpected result: {result.reason}")

            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"❌ Cancellation reason: {cancellation.reason}")
                print(f"❌ Error details: {cancellation.error_details}")

            raise RuntimeError("Azure TTS synthesis failed")

    except Exception as e:
        print(f"🔥 Azure TTS ERROR: {e}")
        raise RuntimeError("Azure TTS generation failed") from e

    # -------------------------------------------------
    # ✅ VALIDATE FILE
    # -------------------------------------------------
    if not output_path.exists():
        raise RuntimeError("TTS file was not created")

    if output_path.stat().st_size == 0:
        try:
            output_path.unlink()
        except Exception:
            pass
        raise RuntimeError("TTS output file is empty")

    print(f"✅ Azure TTS complete → {output_path}")

    return str(output_path)

