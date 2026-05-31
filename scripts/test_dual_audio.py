import sys
import os

# ✅ Add project root to path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

# ✅ Add scripts folder to path
SCRIPT_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.append(SCRIPT_DIR)

# ✅ Now imports will work reliably
from build_blend import build_blend
from podpal.audio.audio_builder import build_audio_from_blend


def run_test():
    print("\n🎧 Starting test...\n")

    query = "Failure is not the end"

    # ✅ Build blend
    blend = build_blend(query)

    print(f"✅ Blend created with {len(blend)} steps")

    # ✅ Generate audio
    audio_path = build_audio_from_blend(blend)

    print("\n🎧 DONE")
    print("Audio file:", audio_path)


if __name__ == "__main__":
    run_test()