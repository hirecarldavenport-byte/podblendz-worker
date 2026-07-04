from scripts.build_blend import build_blend
from podpal.audio.builder import AudioBuilder, ClipRange, AudioOptions
from datetime import datetime, UTC
from podpal.db.database import (
    SessionLocal
)
from podpal.db.blend_store import (
    create_blend
)
import uuid
import os
import asyncio
import edge_tts
from openai import OpenAI
from pydub import AudioSegment
import hashlib
import traceback

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
    
    
    except Exception as e:
    
        print("\n===== TTS ERROR =====")
        print(type(e))
        print(str(e))
        traceback.print_exc()
        print("=====================\n")
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
# ✅ DUPLICATE FILTER (SAFE MODE)
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
# ✅ SOURCE NARRATION
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


You are introducing a podcast clip.

Podcast: {show_name}

Write ONE short sentence.
Mention the speaker if known.
Do not summarize broadly.
Do not say "in this clip" or "this segment."

Examples:

"From Hidden Brain, a look at how stories build empathy."

"Lex Fridman reflects on why books shape identity."

"Diary of a CEO explores the lifelong impact of learning."

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

def run_test(query="How much should I sleep each night?"):
    print("🚀 Running PodBlendz test...\n")

    blend = build_blend(query)

    if not blend:
        print("❌ No blend generated.")
        return

    print(f"✅ Blend steps: {len(blend)}")

    blend_id = str(uuid.uuid4())
    os.makedirs("media", exist_ok=True)

    final_clips = []

    LEAD_PADDING_MS = 4000
    TRAIL_PADDING_MS = 12000

    last_audio = None
    current_group = None

    # =========================
    # ✅ GLOBAL INTRO
    # =========================

    intro_text = generate_podblendz_intro(query)
    intro_audio = generate_tts(intro_text, f"media/{uuid.uuid4()}_intro.mp3")

    if intro_audio:
        final_clips.append(ClipRange(intro_audio, 0, 60000))

    silence = create_silence(700, f"media/{uuid.uuid4()}_silence.mp3")
    final_clips.append(ClipRange(silence, 0, 700))

    # =========================
    # ✅ EXECUTE BLEND
    # =========================

    for step in blend:

        if len(final_clips) > 65:
            break

        # -------------------------
        # 🎙️ NARRATION
        # -------------------------
        if step["type"] == "narration":

            # ✅ FIX: flush clip BEFORE narration
            if current_group:
                final_clips.append(ClipRange(**current_group))
                current_group = None

            text = step.get("text")
            if not text:
                continue

            tts = generate_tts(text, f"media/{uuid.uuid4()}_narration.mp3")

            if tts:
                final_clips.append(ClipRange(tts, 0, 60000))

                pause = create_silence(500, f"media/{uuid.uuid4()}_silence.mp3")
                final_clips.append(ClipRange(pause, 0, 500))

            last_audio = None

        # -------------------------
        # 🎧 SPEAKER
        # -------------------------
        elif step["type"] == "speaker":

            text = step.get("text")
            if not text:
                continue

            # ✅ TEMP disable dedup for debugging
            #temp
            #if is_duplicate(text):
             #continue

            audio_file = step.get("audio_file")
            start = step.get("start")
            end = step.get("end")

            if not audio_file or start is None or end is None:
                continue

            # ✅ SOURCE CHANGE
            is_new_source = last_audio != audio_file

            introduced_sources = set()

            if is_new_source and audio_file not in introduced_sources:
                if current_group:
                    final_clips.append(ClipRange(**current_group))
                    current_group = None
            
                introduced_sources.add(audio_file)

                print("\n🎙 SOURCE INTRO")
                print("audio_file:", audio_file)
                print("text:", text[:120])
                
                source_intro = generate_source_narration(
                    audio_file,
                      text,
                        query
                    )
                print("intro:", source_intro)

                tts = generate_tts(
                    source_intro,
                    f"media/{uuid.uuid4()}_source.mp3"
                    
                    )
                print("tts:", tts)

                if tts:
                    final_clips.append(
                        ClipRange(tts, 0, 60000)
                        )

                    pause = create_silence(
                        400,
                        f"media/{uuid.uuid4()}_silence.mp3"
                        
                        )
                    final_clips.append(
                        ClipRange(pause, 0, 400))

                # ✅ flush before switching source
                if current_group:
                    final_clips.append(ClipRange(**current_group))
                    current_group = None

            # ✅ EXPAND CLIP WINDOW
            start_ms = max(0, int(start * 1000) - LEAD_PADDING_MS)
            end_ms = int(end * 1000) + TRAIL_PADDING_MS

            # ✅ enforce minimum length
            if end_ms - start_ms < 15000:
                end_ms += 15000

            # ✅ GROUPING FIX
            if last_audio == audio_file and current_group:
                current_group["end_ms"] = max(current_group["end_ms"], end_ms)

            else:
                if current_group:
                    final_clips.append(ClipRange(**current_group))

                current_group = {
                    "clip_id": audio_file,
                    "start_ms": start_ms,
                    "end_ms": end_ms
                }

            last_audio = audio_file

        # -------------------------
        # ⏸️ PAUSE
        # -------------------------
        elif step["type"] == "pause":

            duration = int(step.get("duration", 0.5) * 1000)

            silence = create_silence(duration, f"media/{uuid.uuid4()}_silence.mp3")
            final_clips.append(ClipRange(silence, 0, duration))

    # ✅ FINAL FLUSH (CRITICAL)
    if current_group:
        final_clips.append(ClipRange(**current_group))

    print(f"✅ Final timeline segments: {len(final_clips)}")

    print("\n=== TIMELINE ===")
    for i, clip in enumerate(final_clips[:20]):
        print(i, clip)

    # =========================
    # ✅ BUILD AUDIO
    # =========================

    builder = AudioBuilder()

    output_path, duration = builder.build(
        blend_id=blend_id,
        clips=final_clips,
        options=AudioOptions(),
    )

    creators = set()
    podcasts = set()
    episodes = set()
    for step in blend:
        if step.get("type") != "speaker":
            continue
        print("\nSPEAKER STEP KEYS")
        print(step.keys())
        source = step.get(
             "source",
             ""
        )
        podcast_title = step.get(
            "podcast_title",
            ""
        )
        if source:
            podcasts.add(source)
        if podcast_title:
            creators.add(podcast_title)

    metadata = {
            "id": blend_id,
            "title":
                f"{query}: Shared Perspectives",
            "summary":
                f"A PodBlendz conversation about {query}.",
            "description":
                f"Generated blend exploring {query}.",
        "query":
             query,
        "audio_file":
             output_path,
        "image":
            "default.jpg",
        "duration_ms": 
            duration,
        "clip_count":
            len(final_clips),
        "creators":
            sorted(list(creators)),
        "episodes":
            sorted(list(episodes)),
        "podcasts":
            sorted(list(podcasts)),
        "topics":
            [query],
        "confidence": {
            "score": 0,
            "label": "Pending",
            "corroboration_count": 0
        },
        "created_at":
            datetime.now(UTC)
        }
    print(
        f"Episodes Found: {len(episodes)}"
    )
    print(
        sorted(list(episodes))[:5]
    )
    db = SessionLocal()
    try:
            create_blend(
             db,
             metadata
            )
            print(
                f"✅ Blend saved to database: "
                f"{blend_id}"
            )
    finally:
            db.close()

    print("\n🎧 SUCCESS!")
    print(f"📂 Output: {output_path}")
    print(f"⏱️ Duration: {duration / 1000:.2f} seconds")

if __name__ == "__main__":
    run_test()

