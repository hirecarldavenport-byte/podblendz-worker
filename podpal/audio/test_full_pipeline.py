from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions
import uuid
import os
import asyncio
import edge_tts
from openai import OpenAI

client = OpenAI()


# =========================
# ✅ TTS
# =========================

async def tts_to_file(text, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-JennyNeural"
    )
    await communicate.save(output_path)


def generate_tts(text, path):
    try:
        asyncio.run(tts_to_file(text, path))
        return path
    except Exception as e:
        print(f"⚠️ TTS failed: {e}")
        return None


# =========================
# ✅ DUPLICATE FILTER
# =========================

seen_texts = set()

def is_duplicate(text):
    key = text[:80].lower()
    if key in seen_texts:
        return True
    seen_texts.add(key)
    return False


# =========================
# ✅ SOURCE-AWARE NARRATION
# =========================

def generate_source_narration(source_path, text, query):
    # ✅ SAFE DEFAULT FIRST (fixes your error)
    show_name = "this podcast"

    try:
        parts = source_path.split("/")
        if len(parts) > 2:
            show_name = parts[-2].replace("_", " ").title()  # ✅ optional upgrade here

        prompt = f"""
You are narrating a curated podcast experience.

Topic: {query}

Source: {show_name}

Content:
"{text}"

Introduce this clip and explain what the listener will hear.
Be confident, clear, and natural.
Do NOT repeat the content.

Max 16 words.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content or ""
        return content.strip()

    except Exception:
        return f"This next clip comes from {show_name}."


# =========================
# ✅ MAIN PIPELINE
# =========================

def run_test(query="CRISPR gene editing"):
    print("🚀 Running PodBlendz test...\n")

    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    print(f"✅ Blend steps: {len(blend)}")

    blend_id = str(uuid.uuid4())
    os.makedirs("media", exist_ok=True)

    final_clips = []

    # ✅ CRITICAL: Better natural speech boundaries
    LEAD_PADDING_MS = 8000
    TRAIL_PADDING_MS = 30000

    last_audio = None
    current_group = None
    narration_counter = 0

    for step in blend:

        # =========================
        # 🎙️ EXISTING NARRATION
        # =========================
        if step["type"] == "narration":

            text = step.get("text")
            if not text:
                continue

            tts_path = f"media/{uuid.uuid4()}_narration.mp3"
            tts_file = generate_tts(text, tts_path)

            if tts_file:
                final_clips.append(
                    ClipRange(tts_file, 0, 60000)
                )

            # reset grouping (important for clean transitions)
            last_audio = None
            current_group = None

        # =========================
        # 🎧 SPEAKER
        # =========================
        elif step["type"] == "speaker":

            text = step.get("text")

            # ✅ REMOVE DUPLICATES EARLY
            if not text or is_duplicate(text):
                continue

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")

            if not audio_file or start is None or end is None:
                continue

            narration_counter += 1

            # ✅ SOURCE-BASED NARRATION (LESS FREQUENT)
            if narration_counter % 2 == 0:

                source_text = generate_source_narration(audio_file, text, query)

                tts_path = f"media/{uuid.uuid4()}_source.mp3"
                tts_file = generate_tts(source_text, tts_path)

                if tts_file:
                    final_clips.append(
                        ClipRange(tts_file, 0, 60000)
                    )

                # break continuity cleanly before new segment
                last_audio = None
                current_group = None

            # ✅ EXPANDED CLIP RANGE (KEY FIX)
            start_ms = max(0, int(start * 1000) - LEAD_PADDING_MS)
            end_ms = int(end * 1000) + TRAIL_PADDING_MS

            # ✅ SMART MERGING
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

        # =========================
        # ⏸️ PAUSE
        # =========================
        elif step["type"] == "pause":
            continue

    print(f"✅ Final timeline segments: {len(final_clips)}")

    if not final_clips:
        print("❌ No clips to build.")
        return

    builder = AudioBuilder()

    output_path, duration = builder.build(
        blend_id=blend_id,
        clips=final_clips,
        options=AudioOptions(),
    )

    print("\n🎧 SUCCESS!")
    print(f"📂 Output: {output_path}")
    print(f"⏱️ Duration: {duration / 1000:.2f} seconds")


# =========================
# ✅ RUN
# =========================

if __name__ == "__main__":
    run_test()

