from scripts.build_blend import build_blend
from podpal.audio.tts import generate_dual_voice_audio


def run_test():
    print("\n🎧 Starting test...\n")

    query = "artificial intelligence"

    # ✅ Step 1: build the narrative structure
    blend = build_blend(query)

    print(f"✅ Blend created with {len(blend)} steps")

    # ✅ Step 2: generate audio
    audio_path = generate_dual_voice_audio(blend)

    print("\n🎧 DONE")
    print("Audio file:", audio_path)


if __name__ == "__main__":
    run_test()