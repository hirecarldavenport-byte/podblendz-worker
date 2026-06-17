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

import azure.cognitiveservices.speech as speechsdk

client = OpenAI()

# =========================
# ✅ UTIL
# =========================

def uid():
    return str(uuid.uuid4())


# =========================
# ✅ EDGE TTS (FALLBACK)
# =========================

async def tts_to_file(text, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-JennyNeural"
    )
    await communicate.save(output_path)

def fallback_tts(text, path):
    try:
        asyncio.run(tts_to_file(text, path))
        return path
    except Exception:
        print("⚠️ Fallback TTS failed")
        return None


# =========================
# ✅ AZURE TTS (PRIMARY)
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

        return fallback_tts(text, path)

    except Exception:
        return fallback_tts(text, path)


# =========================
# ✅ SILENCE
# =========================

def create_silence(duration_ms, path):
    silence = AudioSegment.silent(duration=duration_ms)
    silence.export(path, format="mp3")
    return path


# =========================
# ✅ INTRO
# =========================

def generate_intro(query):
    prompt = f"""
You are the host of PodBlendz.

Create a punchy podcast intro.

Topic: {query}

Keep it:
- engaging
- modern
- natural

Max 18 words.
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return (res.choices[0].message.content or "").strip()
    except:
        return f"From PodBlendz, exploring {query}."


# =========================
# ✅ SOURCE NARRATION
# =========================

def generate_source_narration(source_path, text):
    show_name = source_path.split("/")[-2] if "/" in source_path else "this podcast"

    prompt = f"""
Introduce this podcast clip naturally.

Source: {show_name}

Make it:
- short
- contextual
- intriguing

Max 14 words.
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return (res.choices[0].message.content or "").strip()
    except:
        return f"From {show_name}, here's a perspective."


# =========================
# ✅ MAIN PIPELINE
# =========================

def run_test(query="future of AI"):
    print(f"\n🚀 Generating blend for: {query}\n")

    blend_steps = build_blend(query)

    if not blend_steps:
        print("❌ No blend produced")
        return

    blend_id = uid()
    os.makedirs("media", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    final_clips = []
    timeline_segments = []

    print(f"✅ Steps: {len(blend_steps)}")

    # ✅ INTRO
    intro_text = generate_intro(query)
    intro_path = generate_tts(intro_text, f"media/{uid()}_intro.mp3")

    if intro_path:
        final_clips.append(ClipRange(intro_path, 0, 60000))

    final_clips.append(ClipRange(create_silence(600, f"media/{uid()}.mp3"), 0, 600))

    last_audio = None

    # =========================
    # ✅ PROCESS STEPS
    # =========================

    for step in blend_steps:

        if step["type"] == "narration":
            text = step.get("text")
            if not text:
                continue

            tts = generate_tts(text, f"media/{uid()}_narration.mp3")

            if tts:
                final_clips.append(ClipRange(tts, 0, 60000))

        elif step["type"] == "speaker":
            audio = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")
            text = step.get("text")

            if not audio or start is None or end is None:
                continue

            # ✅ Source narration only when changing speaker
            if audio != last_audio:
                intro = generate_source_narration(audio, text)
                tts = generate_tts(intro, f"media/{uid()}_src.mp3")

                if tts:
                    final_clips.append(ClipRange(tts, 0, 60000))

            start_ms = int(start * 1000)
            end_ms = int(end * 1000)

            final_clips.append(
                ClipRange(
                    clip_id=audio,
                    start_ms=start_ms,
                    end_ms=end_ms
                )
            )

            timeline_segments.append({
                "audio": audio,
                "start": start,
                "end": end,
                "text": text
            })

            last_audio = audio

    # ✅ BUILD AUDIO
    builder = AudioBuilder()

    output_path, duration = builder.build(
        blend_id=blend_id,
        clips=final_clips,
        options=AudioOptions()
    )

    print("\n🎧 SUCCESS")
    print(f"📂 {output_path}")
    print(f"⏱ {duration/1000:.2f}s")

    # ✅ SAVE METADATA (CRITICAL FOR UI)

    record = {
        "id": blend_id,
        "title": query,
        "audio_file": output_path,
        "duration": duration,
        "segment_count": len(timeline_segments),
        "segments": timeline_segments
    }

    with open("data/generated_blends.json", "a") as f:
        f.write(json.dumps(record) + "\n")

    print("✅ Saved to generated_blends.json")


# =========================
# ✅ RUN
# =========================

if __name__ == "__main__":
    run_test()


