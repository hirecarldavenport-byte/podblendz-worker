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
# ✅ DATELINE-STYLE ANCHOR
# =========================

def generate_anchor_narration(prev_text, curr_text, query):
    try:
        prompt = f"""
You are guiding a listener through a curated story.

Topic: {query}

Previous idea:
"{prev_text}"

Next clip:
"{curr_text}"

Set up what the listener is about to hear AND why it matters.
Be clear, grounded, and intentional — not vague.
Max 16 words.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content or ""
        return content.strip()

    except Exception:
        return "This next perspective adds an important layer to the story."


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

    # ✅ CRITICAL: asymmetric padding
    LEAD_PADDING_MS = 8000
    TRAIL_PADDING_MS = 28000   # longer tail for thought completion

    last_audio = None
    current_group = None
    previous_text = None

    # ✅ control narration frequency
    anchor_counter = 0

    for step in blend:

        # =========================
        # 🎙️ ORIGINAL NARRATION
        # =========================
        if step["type"] == "narration":

            text = step.get("text")
            if not text:
                continue

            tts_path = f"media/{uuid.uuid4()}_narration.mp3"
            tts_file = generate_tts(text, tts_path)

            if tts_file:
                final_clips.append(
                    ClipRange(
                        clip_id=tts_file,
                        start_ms=0,
                        end_ms=60000
                    )
                )

            last_audio = None
            current_group = None

        # =========================
        # 🎧 SPEAKER
        # =========================
        elif step["type"] == "speaker":

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")
            text = step.get("text")

            if not audio_file or start is None or end is None:
                continue

            # ✅ Reduce narration frequency (IMPORTANT)
            anchor_counter += 1

            if previous_text and anchor_counter % 2 == 0:

                anchor_text = generate_anchor_narration(previous_text, text, query)

                anchor_path = f"media/{uuid.uuid4()}_anchor.mp3"
                anchor_file = generate_tts(anchor_text, anchor_path)

                if anchor_file:
                    final_clips.append(
                        ClipRange(
                            clip_id=anchor_file,
                            start_ms=0,
                            end_ms=60000
                        )
                    )

                last_audio = None
                current_group = None

            # ✅ Expanded clip window (KEY FIX)
            start_ms = max(0, int(start * 1000) - LEAD_PADDING_MS)
            end_ms = int(end * 1000) + TRAIL_PADDING_MS

            # ✅ Merge segments safely
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
            previous_text = text

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


if __name__ == "__main__":
    run_test()

