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
# ✅ MAIN PIPELINE
# =========================

def run_test(query="CRISPR gene editing"):
    print("🚀 Running PodBlendz test...\n")

    # -------------------------
    # ✅ Step 1: Build narrative plan
    # -------------------------
    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    print(f"✅ Blend steps: {len(blend)}")

    blend_id = str(uuid.uuid4())
    os.makedirs("media", exist_ok=True)

    final_clips = []

    # ✅ Critical for restoring natural audio flow
    PADDING_MS = 12000

    # ✅ Track grouping
    last_audio = None
    current_group = None

    # -------------------------
    # ✅ Step 2: Execute blend (DO NOT override it)
    # -------------------------
    for step in blend:

        # =========================
        # 🎙️ NARRATION (from build_blend)
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
                        end_ms=60000  # safe upper bound
                    )
                )

            # reset grouping so narration separates segments cleanly
            last_audio = None
            current_group = None

        # =========================
        # 🎧 SPEAKER (REAL AUDIO)
        # =========================
        elif step["type"] == "speaker":

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")

            if not audio_file or start is None or end is None:
                continue

            # ✅ Expand clip range (restores context)
            start_ms = max(0, int(start * 1000) - PADDING_MS)
            end_ms = int(end * 1000) + PADDING_MS

            # ✅ Merge consecutive same-audio segments
            if last_audio == audio_file and current_group:
                current_group["end_ms"] = end_ms
            else:
                current_group = {
                    "clip_id": audio_file,
                    "start_ms": start_ms,
                    "end_ms": end_ms
                }
                final_clips.append(ClipRange(**current_group))

            last_audio = audio_file

        # =========================
        # ⏸️ PAUSE (optional for now)
        # =========================
        elif step["type"] == "pause":
            # You can implement silence later if needed
            continue

    print(f"✅ Final timeline segments: {len(final_clips)}")

    if not final_clips:
        print("❌ No clips to build.")
        return

    # -------------------------
    # ✅ Step 3: Build audio
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


# =========================
# ✅ RUN
# =========================
if __name__ == "__main__":
    run_test()

