"""
Improved Chunking + Tagging

✅ Removes podcast intros
✅ Creates idea-based chunks
✅ Adds tags (insight, reflection, example)
✅ Preserves audio_path + timestamps (CRITICAL)
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("processed_chunks")


# =========================
# FILTER (REMOVE INTRO NOISE)
# =========================
def is_useful_segment(text: str) -> bool:
    text_lower = text.lower()

    bad_phrases = [
        "welcome to",
        "this is",
        "i'm your host",
        "today's episode",
    ]

    return not any(phrase in text_lower for phrase in bad_phrases)


# =========================
# TAGGING
# =========================
def tag_text(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["for example", "for instance", "example"]):
        return "example"

    if any(x in t for x in ["why", "how", "what if"]):
        return "reflection"

    if any(x in t for x in ["this means", "this suggests", "the idea is"]):
        return "insight"

    if len(t.split()) < 15:
        return "filler"

    return "context"


# =========================
# CHUNKING LOGIC
# =========================
def build_chunks(segments):
    chunks = []
    current = []
    word_count = 0

    for seg in segments:
        text = seg.get("text", "")

        if not is_useful_segment(text):
            continue

        current.append(seg)
        word_count += len(text.split())

        if word_count >= 80:
            chunks.append(current)
            current = []
            word_count = 0

    if current:
        chunks.append(current)

    return chunks


# =========================
# MAIN PROCESS
# =========================
def process_transcript(transcript_path: str):

    print(f"[CHUNK] Processing: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    podcast_id = data.get("podcast_id")
    episode_id = data.get("episode_id")

    # ✅ CRITICAL: MUST exist
    audio_path = data.get("audio_path")

    if not audio_path:
        raise ValueError(
            "❌ Missing audio_path in transcript file. Fix transcription step."
        )

    chunks = build_chunks(segments)
    processed = []

    for chunk in chunks:

        full_text = " ".join(s.get("text", "") for s in chunk).strip()

        if not full_text:
            continue

        start = chunk[0].get("start")
        end = chunk[-1].get("end")

        # ✅ VALIDATION
        if start is None or end is None:
            continue

        processed.append({
            "text": full_text,
            "tag": tag_text(full_text),

            # ✅ REQUIRED FOR AUDIO CLIPPING
            "audio_path": audio_path,
            "start": float(start),
            "end": float(end),
        })

    out_dir = OUTPUT_DIR / podcast_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{episode_id}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "podcast_id": podcast_id,
            "episode_id": episode_id,
            "chunks": processed,
        }, f, indent=2)

    print(f"[CHUNK] Saved: {out_path}")

    return str(out_path)
