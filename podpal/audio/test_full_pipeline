from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions
import uuid


def run_test(query="CRISPR gene editing"):
    print("🚀 Running PodBlendz test...\n")

    # ✅ Step 1: Build logical blend
    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    print(f"✅ Blend steps: {len(blend)}")

    # ✅ Step 2: Convert to audio clips
    clips = []

    for step in blend:
        if step["type"] != "speaker":
            continue  # skip narration for now (test real audio first)

        audio_file = step.get("audio_file")
        start = step.get("start")
        end = step.get("end")

        if not audio_file:
            print("⚠️ Missing audio_file")
            continue

        clips.append(
            ClipRange(
                clip_id=audio_file,
                start_ms=int(start * 1000),
                end_ms=int(end * 1000),
            )
        )

    if not clips:
        print("❌ No valid audio clips found.")
        return

    print(f"✅ Audio clips: {len(clips)}")

    # ✅ Step 3: Build final audio
    builder = AudioBuilder()

    output_path, duration = builder.build(
        blend_id=str(uuid.uuid4()),
        clips=clips,
        options=AudioOptions(),
    )

    print(f"\n🎧 SUCCESS!")
    print(f"📂 Output: {output_path}")
    print(f"⏱️ Duration: {duration / 1000:.2f} seconds")


if __name__ == "__main__":
    run_test()