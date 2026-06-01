from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions
import uuid
import os
import asyncio
import edge_tts
from openai import OpenAI

client = OpenAI()


# =========================
# ✅ TTS HELPERS
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
# ✅ NARRATION
# =========================

def generate_intro(query):
    try:
        prompt = f"""
        Create a short, engaging podcast introduction about: {query}.
        Keep it under 2 sentences and conversational.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content or ""
        return content.strip()

    except Exception:
        # ✅ fallback if API fails
        return f"Here's what you need to know about {query}."


def generate_transition():
    return "Let's take a deeper look at this."


# =========================
# ✅ MAIN TEST
# =========================

def run_test(query="CRISPR gene editing"):
    print("🚀 Running PodBlendz test...\n")

    # -------------------------
    # ✅ Step 1: Build logical blend
    # -------------------------
    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    print(f"✅ Blend steps: {len(blend)}")

    # -------------------------
    # ✅ Step 2: Extract clips
    # -------------------------
    base_clips = []

    for step in blend:
        if step["type"] != "speaker":
            continue

        audio_file = step.get("audio_file")
        start = step.get("start")
        end = step.get("end")

        if not audio_file:
            continue

        base_clips.append(
            ClipRange(
                clip_id=audio_file,
                start_ms=int(start * 1000),
                end_ms=int(end * 1000),
            )
        )

    if not base_clips:
        print("❌ No valid audio clips found.")
        return

    print(f"✅ Audio clips: {len(base_clips)}")

    # -------------------------
    # ✅ Step 3: Generate narration
    # -------------------------
    blend_id = str(uuid.uuid4())
    os.makedirs("media", exist_ok=True)

    final_clips = []

    # ✅ INTRO
    intro_text = generate_intro(query)
    intro_path = f"media/{blend_id}_intro.mp3"

    intro_file = generate_tts(intro_text, intro_path)
    if intro_file:
        final_clips.append(
            ClipRange(clip_id=intro_file, start_ms=0, end_ms=10000)
        )

    # ✅ CLIPS + TRANSITIONS
    for i, clip in enumerate(base_clips):

        if i > 0:
            trans_text = generate_transition()
            trans_path = f"media/{blend_id}_trans_{i}.mp3"

            trans_file = generate_tts(trans_text, trans_path)

            if trans_file:
                final_clips.append(
                    ClipRange(clip_id=trans_file, start_ms=0, end_ms=10000)
                )

        final_clips.append(clip)

    print(f"✅ Final timeline segments: {len(final_clips)}")

    # -------------------------
    # ✅ Step 4: Build audio
    # -------------------------
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
