import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# Load env
load_dotenv()

key = os.getenv("AZURE_SPEECH_KEY")
region = os.getenv("AZURE_SPEECH_REGION")

print("KEY loaded:", bool(key))
print("REGION:", region)

if not key or not region:
    raise RuntimeError("Missing Azure credentials")

# Configure
speech_config = speechsdk.SpeechConfig(subscription=key, region=region)

audio_config = speechsdk.audio.AudioOutputConfig(filename="test.wav")

synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config,
    audio_config=audio_config
)

# ✅ VERY SIMPLE TEXT
text = "Hello. This is a test of Azure speech synthesis."

print("🎙 Generating test audio...")

result = synthesizer.speak_text_async(text).get()

if result is None:
    raise RuntimeError("No result returned")

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print("✅ SUCCESS → test.wav created")
else:
    print("❌ FAILED:", result.reason)

