"""
chunk_and_tag.py

✅ Converts transcripts → structured chunks
✅ Adds tagging (insight, reflection, example)
✅ Preserves audio_path + timestamps (CRITICAL)
✅ Filters intro noise
✅ Outputs data ready for clustering + blending
"""

import json
from pathlib import Path


# -------------------------------------------------
# ✅ CONFIG
# -------------------------------------------------
TRANSCRIPTS_DIR = Path("transcripts")
OUTPUT_DIR = Path("processed_chunks")


# -------------------------------------------------
# ✅ FILTER (REMOVE INTRO NOISE)
# -------------------------------------------------
def is_useful_segment(text: str) -> bool:
    text_lower = text.lower()

    bad_phrases = [
        "welcome to",
        "i'm your host",
        "today's episode",
        "this is",
    ]

    return not any(p in text_lower for p in bad_phrases)


# -------------------------------------------------
# ✅ TAGGING
# -------------------------------------------------
def tag_text(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["example", "for instance"]):
        return "example"

    if any(x in t for x in ["why", "how", "what if"]):
        return "reflection"

    if any(x in t for x in ["this means", "this suggests", "the idea is"]):
        return "insight"

    if len(t.split()) < 15:
        return "filler"

    return "context"


# -------------------------------------------------
# ✅ BUILD CHUNKS (GROUP SEGMENTS)
# -------------------------------------------------
def build_chunks(segments):

    chunks = []
    current = []
    word_count = 0

    for seg in segments:

        text = seg.get("text", "").strip()

        if not text or not is_useful_segment(text):
            continue

        current.append(seg)
        word_count += len(text.split())

        # ✅ chunk threshold (~30–60 sec speech)
        if word_count >= 80:
            chunks.append(current)
            current = []
            word_count = 0

    if current:
        chunks.append(current)

    return chunks


# -------------------------------------------------
# ✅ PROCESS SINGLE TRANSCRIPT
# -------------------------------------------------
def process_transcript(path: Path):

    print(f"[CHUNK] Processing: {path.name}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    podcast_id = data.get("podcast_id")
    episode_id = data.get("episode_id")

    # ✅ MUST EXIST (critical for audio system)
    audio_path = data.get("audio_path")

    if not audio_path:
        raise ValueError(
            f"❌ Missing audio_path in {path.name}. Fix transcription step."
        )

    chunks = build_chunks(segments)

    processed = []

    for chunk in chunks:

        full_text = " ".join(s.get("text", "") for s in chunk).strip()

        if not full_text:
            continue

        start = chunk[0].get("start")
        end = chunk[-1].get("end")

        # ✅ validate timestamps
        if start is None or end is None:
            continue

        processed.append({
            "text": full_text,
            "tag": tag_text(full_text),

            # ✅ CRITICAL FOR AUDIO
            "audio_path": audio_path,

            # ✅ TIMESTAMPS
            "start": float(start),
            "end": float(end),
        })

    if not processed:
        print(f"⚠️ No usable chunks from {path.name}")
        return

    # ✅ SAVE OUTPUT
    out_dir = OUTPUT_DIR / podcast_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{episode_id}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "podcast_id": podcast_id,
            "episode_id": episode_id,
            "chunks": processed,
        }, f, indent=2)

    print(f"✅ Saved → {out_path}")


# -------------------------------------------------
# ✅ RUN ALL TRANSCRIPTS
# -------------------------------------------------
if __name__ == "__main__":

    print("\n🚀 STARTING CHUNKING PIPELINE\n")

    if not TRANSCRIPTS_DIR.exists():
        raise FileNotFoundError("❌ transcripts/ folder not found")

    files = list(TRANSCRIPTS_DIR.glob("*.json"))

    if not files:
        print("⚠️ No transcript files found")
    else:
        for file in files:
            process_transcript(file)

    print("\n✅ CHUNKING COMPLETE\n")
