"""
Improved Chunking + Tagging

✅ Removes podcast intros
✅ Creates idea-based chunks
✅ Better tagging (reflection vs insight vs example)
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
        "conversations for the curious",
        "today's episode",
    ]

    for phrase in bad_phrases:
        if phrase in text_lower:
            return False

    return True


# =========================
# TAGGING (UPGRADED)
# =========================

def tag_text(text: str) -> str:
    t = text.lower()

    if "example" in t or "for instance" in t or "for example" in t:
        return "example"

    if any(w in t for w in ["why", "how", "what if"]):
        return "reflection"

    if any(w in t for w in ["the idea", "this means", "this suggests"]):
        return "insight"

    if len(t.split()) < 15:
        return "filler"

    return "context"


# =========================
# CHUNKING (BETTER LOGIC)
# =========================

def build_chunks(segments):
    chunks = []
    current = []
    word_count = 0

    for seg in segments:
        text = seg.get("text", "")

        if not is_useful_segment(text):
            continue

        words = text.split()

        current.append(seg)
        word_count += len(words)

        # ✅ better threshold
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

    chunks = build_chunks(segments)

    processed = []

    for chunk in chunks:
        full_text = " ".join(s.get("text", "") for s in chunk)

        processed.append({
            "text": full_text.strip(),
            "tag": tag_text(full_text),
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
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
