from scripts.search_faiss import search
from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# =========================
# ✅ HELPERS
# =========================

def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


def safe_content(response):
    try:
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception:
        return ""


# =========================
# ✅ LIGHT FILTERING (RELAXED)
# =========================

def is_valid_segment(text, duration):
    if not text:
        return False

    if len(text.split()) < 6:
        return False

    if duration < 2:
        return False

    return True


# =========================
# ✅ DEDUP + DIVERSITY
# =========================

def select_diverse_segments(results, max_segments=16):
    selected = []
    seen_texts = set()
    seen_sources = {}

    for r in results:
        text = r.get("text", "").strip()
        audio_file = r.get("audio_file", "")

        key = text[:80].lower()

        if key in seen_texts:
            continue

        # ✅ limit dominance from same source
        if audio_file:
            count = seen_sources.get(audio_file, 0)
            if count >= 3:
                continue
            seen_sources[audio_file] = count + 1

        selected.append(r)
        seen_texts.add(key)

        if len(selected) >= max_segments:
            break

    return selected


# =========================
# ✅ DATELINE-STYLE NARRATION
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"""
Act like a documentary host.

Introduce a compelling idea about:
{query}

Set up what the listener will learn.
Max 22 words.
"""

    elif stage == "bridge":
        prompt = f"""
You are guiding a story.

Previous idea:
"{context}"

Next idea:
"{text}"

Help the listener understand the transition.
Do NOT be vague.

Max 16 words.
"""

    elif stage == "outro":
        prompt = f"""
Close this segment about:
{query}

Leave the listener thinking.
Max 20 words.
"""

    else:
        prompt = f"""
Guide the listener’s understanding of this idea:

"{text}"

Add context without repeating it.
Max 16 words.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return safe_content(response)


# =========================
# ✅ MAIN BUILDER
# =========================

def build_blend(query, max_segments=20):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    # -------------------------
    # ✅ STEP 1: FILTER LIGHTLY
    # -------------------------
    filtered = []

    for r in results:
        text = r.get("text", "").strip()
        start = r.get("start")
        end = r.get("end")

        if start is None or end is None:
            continue

        duration = end - start

        if not is_valid_segment(text, duration):
            continue

        filtered.append(r)

    if not filtered:
        print("❌ No usable segments.")
        return []

    # -------------------------
    # ✅ STEP 2: SORT BY RELEVANCE
    # -------------------------
    filtered = sorted(filtered, key=lambda x: x["score"])

    # -------------------------
    # ✅ STEP 3: DEDUP + DIVERSIFY
    # -------------------------
    selected = select_diverse_segments(filtered, max_segments)

    blend = []

    # -------------------------
    # 🎬 INTRO
    # -------------------------
    intro = generate_dateline_line("", query=query, stage="intro")

    blend.append({
        "type": "narration",
        "text": intro
    })

    blend.append({"type": "pause", "duration": 0.6})

    # -------------------------
    # 🎬 MAIN FLOW
    # -------------------------
    for i, seg in enumerate(selected):

        text = seg["text"]
        audio_file = seg.get("audio_file")

        # ✅ STRUCTURED NARRATION (NOT EVERY TIME)
        if i == 0:
            narration = generate_dateline_line("", text, query)

            blend.append({
                "type": "narration",
                "text": narration
            })

            blend.append({"type": "pause", "duration": 0.4})

        elif i % 2 == 0:
            prev = selected[i - 1]

            narration = generate_dateline_line(
                shorten(prev["text"]),
                shorten(text),
                query,
                stage="bridge"
            )

            blend.append({
                "type": "narration",
                "text": narration
            })

            blend.append({"type": "pause", "duration": 0.4})

        # ✅ SPEAKER SEGMENT
        blend.append({
            "type": "speaker",
            "text": text,
            "audio_file": audio_file,
            "start": seg.get("start"),
            "end": seg.get("end"),
            "source": audio_file  # ✅ NEW: enable source narration downstream
        })

        blend.append({"type": "pause", "duration": 0.6})

    # -------------------------
    # 🎬 OUTRO
    # -------------------------
    outro = generate_dateline_line("", query=query, stage="outro")

    blend.append({
        "type": "narration",
        "text": outro
    })

    return blend


# =========================
# ✅ TEST
# =========================

if __name__ == "__main__":
    result = build_blend("financial literacy")

    print("\n🔥 OUTPUT\n")
    for step in result:
        print(step)










