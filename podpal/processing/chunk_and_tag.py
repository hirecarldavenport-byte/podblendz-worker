"""
chunk_and_tag Converts transcripts → structured chunkschunk_and_tag.py
✅ Uses S3 audio paths (FIXED)
✅ Preserves timestamps
✅ Outputs data ready for clustering + blending
"""

import json
from pathlib import Path


# -------------------------------------------------
# ✅ CONFIG
# -------------------------------------------------
TRANSCRIPTS_DIR = Path("transcripts")
OUTPUT_DIR = Path("processed_chunks")

# ✅ YOUR S3 BUCKET (IMPORTANT)
S3_BUCKET = "podblendz-episode-audio"
S3_REGION = "us-east-1"


# -------------------------------------------------
# ✅ FILTER
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
# ✅ BUILD CHUNKS
# -------------------------------------------------
def build_chunks(segments):

    chunks = []
    current = []
    word_count = 0

    for seg in segments:

        text = (seg.get("text") or "").strip()

        if not text or not is_useful_segment(text):
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


# -------------------------------------------------
# ✅ PROCESS TRANSCRIPT
# -------------------------------------------------
def process_transcript(path: Path):

    print(f"[CHUNK] Processing: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    podcast_id = data.get("podcast_id") or "unknown_podcast"
    episode_id = data.get("episode_id") or path.stem
    episode_title = data.get("title")
    published = data.get("published")
    audio_url = data.get("audio_url")
    s3_key = data.get("s3_key")


    # ✅ FIXED: ALWAYS USE S3 PATH
    s3_key = f"raw_audio/{podcast_id}/{episode_id}.mp3"

    audio_path = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"

    if not segments:
        print(f"⚠️ Skipping {path.name} (no segments)")
        return

    chunks = build_chunks(segments)
    processed = []

    for chunk in chunks:

        full_text = " ".join(
            (s.get("text") or "") for s in chunk
        ).strip()

        if not full_text:
            continue

        start = chunk[0].get("start")
        end = chunk[-1].get("end")

        if start is None or end is None:
            continue

        processed.append({
            "text": full_text,
            "tag": tag_text(full_text),
            "episode_title": episode_title,
            "published": published,
            "podcast_id": podcast_id,
            "episode_id": episode_id,

            # ✅ CRITICAL CHANGE HERE
            "audio_path": audio_path,
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
             # ✅ Episode metadata
             "episode_title": episode_title,
             "published": published,
             "audio_url": audio_url,
             "s3_key": s3_key,

            "chunks": processed,
        }, f, indent=2)

        print(
             f"[CHUNK] "
             f"{episode_id} -> "
             f"{episode_title}"
        )

    print(f"✅ Saved → {out_path}")
    return str(out_path)


# -------------------------------------------------
# ✅ RUN
# -------------------------------------------------
if __name__ == "__main__":

    print("\n🚀 STARTING CHUNKING PIPELINE\n")

    if not TRANSCRIPTS_DIR.exists():
        raise FileNotFoundError("❌ transcripts/ folder not found")

    files = list(TRANSCRIPTS_DIR.rglob("*.json"))

    if not files:
        print("⚠️ No transcript files found")
    else:
        print(f"✅ Found {len(files)} transcript files\n")

        for file in files:
            process_transcript(file)

    print("\n✅ CHUNKING COMPLETE\n")


