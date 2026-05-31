# podpal/audio/tts.py

from __future__ import annotations

import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk


# -------------------------------------------------
# ✅ LOAD ENV
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
# ✅ TEXT PROCESSING
# -------------------------------------------------
MAX_CHARS = 2500  # safe Azure chunk size


def chunk_text(text: str) -> List[str]:
    """Split long text into safe chunks for Azure."""
    return [
        text[i:i + MAX_CHARS]
        for i in range(0, len(text), MAX_CHARS)
    ]


def add_pauses(text: str) -> str:
    """Improve pacing with natural pauses."""
    sentences = text.split(". ")
    return ". <break time='500ms'/> ".join(sentences)


def build_ssml(text: str, voice: str) -> str:
    """Generate SSML for better voice delivery."""
    return f"""
<speak version="1.0" xml:lang="en-US">
  <voice name="{voice}">
    <prosody rate="0.92" pitch="+2%">
      <emphasis level="moderate">
        {text}
      </emphasis>
    </prosody>
  </voice>
</speak>
"""


# -------------------------------------------------
# ✅ CORE SYNTH FUNCTION (PER CHUNK)
# -------------------------------------------------
def _synthesize_chunk(text: str, output_path: Path, voice: str):
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_Endpoint,
        f"https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    )

    speech_config.speech_synthesis_voice_name = voice

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=str(output_path)
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    ssml = build_ssml(add_pauses(text), voice)

    result: Optional[speechsdk.SpeechSynthesisResult] = (
        synthesizer.speak_ssml_async(ssml).get()
    )

    if not result:
        raise RuntimeError("Azure TTS returned no result")

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            print(f"❌ Cancellation reason: {cancellation.reason}")
            print(f"❌ Error details: {cancellation.error_details}")

        raise RuntimeError("Azure TTS synthesis failed")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("TTS output file invalid")


# -------------------------------------------------
# ✅ MAIN PUBLIC FUNCTION
# -------------------------------------------------
def generate_audio(
    text: str,
    voice: str = "en-US-JennyNeural",
    filename_prefix: str = "blend",
) -> str:
    """
    Generate podcast-style TTS using Azure.

    Returns:
        Path to output WAV file.
    """

    print(f"🔐 AZURE KEY LOADED: {bool(AZURE_SPEECH_KEY)}")
    print(f"🌍 AZURE REGION: {AZURE_SPEECH_REGION}")

    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise RuntimeError("❌ Azure Speech is not configured")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]

    chunks = chunk_text(text)

    print(f"🎙 Generating {len(chunks)} audio chunk(s)...")

    chunk_files = []

    # ✅ generate each chunk
    for i, chunk in enumerate(chunks):
        part_file = TTS_DIR / f"{filename_prefix}_{timestamp}_{unique_id}_part{i}.wav"

        print(f"🔊 Chunk {i+1}/{len(chunks)} → {part_file}")

        _synthesize_chunk(chunk, part_file, voice)

        chunk_files.append(part_file)

    # -------------------------------------------------
    # ✅ MERGE AUDIO (simple concatenation)
    # -------------------------------------------------
    final_file = TTS_DIR / f"{filename_prefix}_{timestamp}_{unique_id}.wav"

    with open(final_file, "wb") as outfile:
        for f in chunk_files:
            with open(f, "rb") as infile:
                outfile.write(infile.read())

    # cleanup temp chunk files
    for f in chunk_files:
        try:
            f.unlink()
        except Exception:
            pass

    print(f"✅ Final audio ready → {final_file}")

    return str(final_file)


