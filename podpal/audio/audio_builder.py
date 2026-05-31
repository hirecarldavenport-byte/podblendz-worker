from pydub import AudioSegment
from podpal.audio.tts import generate_audio  # ← your simple TTS
from podpal.audio.clip_extractor import extract_clip

import os
import uuid
from datetime import datetime


def build_audio_from_blend(blend, output_dir="audio/tts"):
    """
    Build final audio using:
    - narrator (TTS)
    - real podcast clips
    """

    final_audio = AudioSegment.silent(duration=0)

    for step in blend:

        if step["type"] == "narration":
            # ✅ Generate narrator audio
            path = generate_audio(step["text"])
            segment = AudioSegment.from_file(path)

        elif step["type"] == "speaker":
            # ✅ Extract REAL audio
            segment = extract_clip(
                audio_file=step["audio_file"],
                start=step["start"],
                end=step["end"],
            )

        elif step["type"] == "pause":
            duration_ms = int(step.get("duration", 0.5) * 1000)
            segment = AudioSegment.silent(duration=duration_ms)

        else:
            continue

        final_audio += segment

    filename = f"blend_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
    output_path = os.path.join(output_dir, filename)

    final_audio.export(output_path, format="mp3")

    print(f"✅ Final hybrid audio → {output_path}")

    return output_path