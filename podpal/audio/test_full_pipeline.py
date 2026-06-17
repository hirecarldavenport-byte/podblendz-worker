from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions

import uuid
import os
import asyncio
import edge_tts
from openai import OpenAI
from pydub import AudioSegment
import hashlib
import json
import nest_asyncio

import azure.cognitiveservices.speech as speechsdk

# ✅ FIX ASYNC LOOP (CRITICAL)
nest_asyncio.apply()

client = OpenAI()

# =========================
# ✅ CONSTANTS (QUALITY TUNING)
# =========================

LEAD_PADDING_MS = 8000
TRAIL_PADDING_MS = 30000
MIN_CLIP_MS = 30000
MAX_CLIPS = 85

USED_TEXTS = set()


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
        loop = asyncio.get_event_loop()
        loop.run_until_complete(tts_to_file(text, path))
        return path
    except Exception as e:
        print("⚠️ Fallback TTS failed:", e)
        return None


# =========================
# ✅ AZURE TTS
# =========================

def generate_tts(text, path):
    try:
        key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")

        if not key or not region:
            return fallback_tts(text, path)

        speech_config = speechsdk.SpeechConfig(
            subscription=key,
            region=region
        )

        speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"

        audio_config = speechsdk.audio.AudioOutputConfig(filename=path)

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        result = synthesizer.speak_text_async(text).get()

        if result and result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return path

        print("⚠️ Azure failed → fallback")
        return fallback_tts(text, path)

    except Exception as e:
        print("⚠️ Azure exception:", e)
        return fallback_tts(text, path)


# =========================
# ✅ SILENCE
# =========================

def create_silence(duration_ms, path):
    silence = AudioSegment.silent(duration=duration_ms)
    silence.export(path, format="mp3")
    return path


# =========================
# ✅ QUALITY FILTERS
# =========================

def is_valid_segment(step):
    if step.get("type") != "speaker":
        return True

    if not step.get("audio_file"):
        return False

    text = step.get("text", "").strip()

    if not text or len(text) < 50:
        return False

    return True


def is_repetitive(text):
    key = " ".join(text.lower().split())

    if key in USED_TEXTS:
        return True

    USED_TEXTS.add(key)
    return False


# =========================
# ✅ INTRO
# =========================

def generate_intro(query):
    try:
        prompt = f"""
You are the host of PodBlendz.
Create a compelling, modern intro.

Topic: {query}

Max 18 words.
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
      
    except:
        return f"From PodBlendz, this explores {query}."


# =========================
# ✅ SOURCE NARRATION
# =========================

def generate_source_narration(audio, text, query):
    try:
        show_name = audio.split("/")[-2] if "/" in audio else "this podcast"

        prompt = f"""
Introduce this clip.

Source: {show_name}
Topic: {query}

Max 12 words.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content
        return content.strip() if content else ""

        

    except:
        return f"From {audio}, here's a perspective."


# =========================
# ✅ MAIN PIPELINE
# =========================

def run_test(query="future of AI"):

    print(f"\n🚀 Generating blend: {query}\n")

    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    blend_id = str(uuid.uuid4())

    os.makedirs("media", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    final_clips = []
    timeline_segments = []

    last_audio = None
    current_group = None

    # ✅ INTRO
    intro_text = generate_intro(query)
    intro_audio = generate_tts(intro_text, f"media/{uuid.uuid4()}_intro.mp3")

    if intro_audio:
        final_clips.append(ClipRange(intro_audio, 0, 60000))

    silence = create_silence(600, f"media/{uuid.uuid4()}_silence.mp3")
    final_clips.append(ClipRange(silence, 0, 600))

    # =========================
    # ✅ MAIN LOOP
    # =========================

    for step in blend:

        if len(final_clips) > MAX_CLIPS:
            print("⚠️ Max clips reached")

            outro_text = f"This has been a PodBlendz blend on {query}."
            outro_audio = generate_tts(outro_text, f"media/{uuid.uuid4()}_outro.mp3")

            if outro_audio:
                final_clips.append(ClipRange(outro_audio, 0, 60000))

            break

        # ✅ FILTER INVALID
        if not is_valid_segment(step):
            continue

        # ✅ NARRATION
        if step["type"] == "narration":

            text = step.get("text")
            if not text:
                continue

            tts = generate_tts(text, f"media/{uuid.uuid4()}_narration.mp3")

            if tts:
                final_clips.append(ClipRange(tts, 0, 60000))

                pause = create_silence(400, f"media/{uuid.uuid4()}_silence.mp3")
                final_clips.append(ClipRange(pause, 0, 400))

            last_audio = None
            continue

        # ✅ SPEAKER
        if step["type"] == "speaker":

            text = step.get("text")

            if is_repetitive(text):
                continue

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")

            if not audio_file or start is None or end is None:
                continue

            is_new_source = last_audio != audio_file

            # ✅ SHORT INTRO
            if is_new_source:
                intro = generate_source_narration(audio_file, text, query)
                tts = generate_tts(intro, f"media/{uuid.uuid4()}_src.mp3")

                if tts:
                    final_clips.append(ClipRange(tts, 0, 60000))

            # ✅ EXTEND CLIPS
            start_ms = max(0, int(start * 1000) - LEAD_PADDING_MS)
            end_ms = int(end * 1000) + TRAIL_PADDING_MS

            # ✅ MIN SIZE
            if end_ms - start_ms < MIN_CLIP_MS:
                end_ms = start_ms + MIN_CLIP_MS

            # ✅ GROUPING
            if last_audio == audio_file and current_group:
                current_group["end_ms"] = max(current_group["end_ms"], end_ms)
            else:
                if current_group:
                    final_clips.append(ClipRange(**current_group))

                current_group = {
                    "clip_id": audio_file,
                    "start_ms": start_ms,
                    "end_ms": end_ms
                }

            timeline_segments.append({
                "audio": audio_file,
                "start": start,
                "end": end,
                "text": text
            })

            last_audio = audio_file

        # ✅ PAUSE
        elif step["type"] == "pause":
            duration = int(step.get("duration", 0.5) * 1000)
            silence = create_silence(duration, f"media/{uuid.uuid4()}_silence.mp3")
            final_clips.append(ClipRange(silence, 0, duration))

    if current_group:
        final_clips.append(ClipRange(**current_group))

    # =========================
    # ✅ BUILD AUDIO
    # =========================

    builder = AudioBuilder()

    output_path, duration = builder.build(
        blend_id=blend_id,
        clips=final_clips,
        options=AudioOptions()
    )

    print("\n🎧 SUCCESS")
    print(f"📂 {output_path}")
    print(f"⏱ {duration / 1000:.2f} seconds")

    # ✅ SAVE METADATA

    record = {
        "id": blend_id,
        "title": query,
        "audio_file": output_path,
        "duration": duration,
        "segments": timeline_segments
    }

    with open("data/generated_blends.json", "a") as f:
        f.write(json.dumps(record) + "\n")

    print("✅ Saved blend metadata")


# =========================
# ✅ RUN
# =========================

if __name__ == "__main__":
    run_test()



