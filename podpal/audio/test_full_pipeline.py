from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions
import uuid
import os
import asyncio
import edge_tts
from openai import OpenAI
from pydub import AudioSegment
import hashlib

client = OpenAI()


# =========================
# ✅ TTS
# =========================

async def tts_to_file(text, output_path):
    communicate = edge_tts.Communicate(text=text, voice="en-US-JennyNeural")
    await communicate.save(output_path)


def generate_tts(text, path):
    try:
        asyncio.run(tts_to_file(text, path))
        return path
    except Exception:
        return None


# =========================
# ✅ SILENCE
# =========================

def create_silence(duration_ms, path):
    silence = AudioSegment.silent(duration=duration_ms)
    silence.export(path, format="mp3")
    return path


# =========================
# ✅ GLOBAL INTRO
# =========================

def generate_podblendz_intro(query):
    try:
        prompt = f"""
You are the host of PodBlendz.

Create a natural podcast intro.

Topic: {query}

Say:
- From PodBlendz...
- what this episode covers
- why it matters

Max 18 words.
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return (response.choices[0].message.content or "").strip()

    except Exception:
        return f"From PodBlendz, this episode explores {query}. Enjoy."


# =========================
# ✅ STRONG DUPLICATE FILTER
# =========================

seen_texts = set()

def is_duplicate(text):
    cleaned = " ".join(text.lower().split())
    key = hashlib.md5(cleaned.encode()).hexdigest()

    if key in seen_texts:
        return True

    seen_texts.add(key)
    return False


# =========================
# ✅ SOURCE NARRATION (FORCED)
# =========================

def generate_source_narration(source_path, text, query):
    show_name = "this podcast"

    try:
        parts = source_path.split("/")
        if len(parts) > 2:
            show_name = parts[-2].replace("_", " ").title()

        prompt = f"""
You are a professional podcast narrator.

Topic: {query}
Source: {show_name}

Clip:
"{text}"

Introduce this segment clearly.
Explain what insight it offers.

Max 16 words.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return (response.choices[0].message.content or "").strip()

    except Exception:
        return f"From {show_name}, this next perspective adds insight."


# =========================
# ✅ MAIN PIPELINE
# =========================

def run_test(query="Mental Health"):
    print("🚀 Running PodBlendz test...\n")

    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    print(f"✅ Blend steps: {len(blend)}")

    blend_id = str(uuid.uuid4())
    os.makedirs("media", exist_ok=True)

    final_clips = []

    LEAD_PADDING_MS = 8000
    TRAIL_PADDING_MS = 30000

    last_audio = None
    current_group = None

    # ✅ GLOBAL INTRO (ALWAYS FIRST)
    intro_text = generate_podblendz_intro(query)
    intro_audio = generate_tts(intro_text, f"media/{uuid.uuid4()}_intro.mp3")

    if intro_audio:
        final_clips.append(ClipRange(intro_audio, 0, 60000))

    # intro breath
    silence = create_silence(700, f"media/{uuid.uuid4()}_silence.mp3")
    final_clips.append(ClipRange(silence, 0, 700))

    # =========================
    # ✅ EXECUTE BLEND
    # =========================

    for step in blend:

        if len(final_clips) > 65:  # ✅ STOP DRIFTING
            break

        # 🎙️ narration
        if step["type"] == "narration":

            text = step.get("text")
            if not text:
                continue

            tts = generate_tts(text, f"media/{uuid.uuid4()}_narration.mp3")

            if tts:
                final_clips.append(ClipRange(tts, 0, 60000))

                pause = create_silence(500, f"media/{uuid.uuid4()}_silence.mp3")
                final_clips.append(ClipRange(pause, 0, 500))

            last_audio = None
            current_group = None

        # 🎧 speaker
        elif step["type"] == "speaker":

            text = step.get("text")
            if not text or is_duplicate(text):
                continue

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")

            if not audio_file or start is None or end is None:
                continue

            # ✅ FORCE SOURCE INTRO when source changes
            is_new_source = last_audio != audio_file

            if is_new_source:
                source_intro = generate_source_narration(audio_file, text, query)

                tts = generate_tts(source_intro, f"media/{uuid.uuid4()}_source.mp3")

                if tts:
                    final_clips.append(ClipRange(tts, 0, 60000))

                    pause = create_silence(400, f"media/{uuid.uuid4()}_silence.mp3")
                    final_clips.append(ClipRange(pause, 0, 400))

                current_group = None

            # ✅ extend clip
            start_ms = max(0, int(start * 1000) - LEAD_PADDING_MS)
            end_ms = int(end * 1000) + TRAIL_PADDING_MS

            if last_audio == audio_file and current_group:
                current_group["end_ms"] = max(current_group["end_ms"], end_ms)
            else:
                current_group = {
                    "clip_id": audio_file,
                    "start_ms": start_ms,
                    "end_ms": end_ms
                }
                final_clips.append(ClipRange(**current_group))

            last_audio = audio_file

        # ⏸️ pause
        elif step["type"] == "pause":
            duration = int(step.get("duration", 0.5) * 1000)

            silence = create_silence(duration, f"media/{uuid.uuid4()}_silence.mp3")
            final_clips.append(ClipRange(silence, 0, duration))

    print(f"✅ Final timeline segments: {len(final_clips)}")

    builder = AudioBuilder()

    output_path, duration = builder.build(
        blend_id=blend_id,
        clips=final_clips,
        options=AudioOptions(),
    )

    print("\n🎧 SUCCESS!")
    print(f"📂 Output: {output_path}")
    print(f"⏱️ Duration: {duration / 1000:.2f} seconds")


if __name__ == "__main__":
    run_test()

