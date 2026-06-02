from scripts.search_faiss import search
from openai import OpenAI
import os
import hashlib

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# =========================
# ✅ HELPERS
# =========================

def normalize(text):
    return " ".join(text.lower().split())


def dedup_key(text):
    return hashlib.md5(normalize(text).encode()).hexdigest()


def safe_llm(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


# =========================
# ✅ AGGRESSIVE AD FILTER
# =========================

def is_ad(text):
    t = text.lower()

    blockers = [
        "sponsor",
        "brought to you",
        "visit",
        "dot com",
        ".com",
        "www",
        "http",
        "subscribe",
        "sign up",
        "promo",
        "support for"
    ]

    return any(b in t for b in blockers)


# =========================
# ✅ MAIN BUILDER
# =========================

def build_blend(query, max_segments=10):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    # -------------------------
    # ✅ FILTER
    # -------------------------
    filtered = []
    seen = set()
    source_count = {}

    for r in results:

        text = r.get("text", "").strip()
        audio_file = r.get("audio_file")
        start = r.get("start")
        end = r.get("end")

        if not text or not audio_file:
            continue

        if is_ad(text):
            continue

        if start is None or end is None:
            continue

        if len(text.split()) < 6:
            continue

        key = dedup_key(text)
        if key in seen:
            continue

        count = source_count.get(audio_file, 0)
        if count >= 3:
            continue

        source_count[audio_file] = count + 1
        seen.add(key)
        filtered.append(r)

        if len(filtered) >= 30:
            break

    if not filtered:
        print("❌ No usable segments.")
        return []

    # -------------------------
    # ✅ SELECT TOP SEGMENTS
    # -------------------------
    selected = filtered[:max_segments]

    blend = []

    # -------------------------
    # ✅ INTRO (FORCED)
    # -------------------------
    intro_prompt = f"""
You are the host of PodBlendz.

Say:
"From PodBlendz, this episode explores {query}."

Then briefly explain what the listener will learn.

Max 20 words.
"""

    intro = safe_llm(intro_prompt)

    if not intro:
        intro = f"From PodBlendz, this episode explores {query} and what it means."

    blend.append({"type": "narration", "text": intro})
    blend.append({"type": "pause", "duration": 0.6})

    # -------------------------
    # ✅ MAIN FLOW (FORCED NARRATION)
    # -------------------------
    for seg in selected:

        text = seg["text"]

        prompt = f"""
Introduce this segment.

Topic: {query}

"{text}"

Explain what the listener is about to hear.

Max 16 words.
"""

        narration = safe_llm(prompt)

        if not narration:
            narration = "In this segment, hear an important perspective on this topic."

        blend.append({"type": "narration", "text": narration})
        blend.append({"type": "pause", "duration": 0.4})

        # ✅ CLIP
        blend.append({
            "type": "speaker",
            "text": text,
            "audio_file": seg.get("audio_file"),
            "start": seg.get("start"),
            "end": seg.get("end"),
        })

        blend.append({"type": "pause", "duration": 0.6})

    # -------------------------
    # ✅ OUTRO
    # -------------------------
    outro_prompt = f"""
Close this podcast about {query} with a clear takeaway.

Max 18 words.
"""

    outro = safe_llm(outro_prompt)

    if not outro:
        outro = "This topic continues to evolve, and there’s much more to explore."

    blend.append({"type": "narration", "text": outro})

    return blend













