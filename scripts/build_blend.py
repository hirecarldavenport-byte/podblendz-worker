from scripts.search_faiss import search
from openai import OpenAI
import os
import hashlib

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
# ✅ FILTERING
# =========================

def is_valid_segment(text, duration):
    if not text or len(text.split()) < 6:
        return False
    if duration < 2:
        return False
    return True


def is_ad(text):
    t = text.lower()

    ad_phrases = [
        "sponsor",
        "brought to you by",
        "this episode is sponsored",
        "thanks to our sponsor",
        "advertisement",
        "promo code",
        "visit our website",
        "support for this podcast",
        "dot com",
        ".com",
        "www.",
        "sign up",
        "subscribe",
        "link in bio"
    ]

    return any(p in t for p in ad_phrases)


# =========================
# ✅ STRONG DEDUP
# =========================

def dedup_key(text):
    cleaned = " ".join(text.lower().split())
    return hashlib.md5(cleaned.encode()).hexdigest()


# =========================
# ✅ DIVERSITY SELECTION
# =========================

def select_segments(results, max_segments=12):
    selected = []
    seen_keys = set()
    seen_sources = {}

    MAX_PER_SOURCE = 3

    for r in results:
        text = r.get("text", "")
        audio_file = r.get("audio_file")

        if not text or not audio_file:
            continue

        key = dedup_key(text)
        if key in seen_keys:
            continue

        count = seen_sources.get(audio_file, 0)
        if count >= MAX_PER_SOURCE:
            continue

        seen_sources[audio_file] = count + 1

        selected.append(r)
        seen_keys.add(key)

        if len(selected) >= max_segments:
            break

    return selected


# =========================
# ✅ NARRATION (FIXED + STRONGER)
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"""
You are the host of PodBlendz.

Start with:
"From PodBlendz..."

Then clearly say:
"This episode explores {query}."

Then briefly explain what the listener will learn.

Speak naturally and clearly.
Max 22 words.
"""

    elif stage == "segment_intro":
        prompt = f"""
Introduce this segment.

Topic: {query}

Clip:
"{text}"

Explain what the listener is about to hear and why it matters.

Max 18 words.
"""

    elif stage == "bridge":
        prompt = f"""
Guide the listener.

Topic: {query}

Previous idea:
"{context}"

Next idea:
"{text}"

Explain how this connects.

Max 18 words.
"""

    elif stage == "outro":
        prompt = f"""
Close this episode about {query}.

Give a clear takeaway.

Max 20 words.
"""

    else:
        return ""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return safe_content(response)


# =========================
# ✅ MAIN BUILDER
# =========================

def build_blend(query, max_segments=12):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    # ✅ STEP 1: CLEAN FILTER
    filtered = []

    for r in results:
        text = r.get("text", "").strip()
        start = r.get("start")
        end = r.get("end")
        audio_file = r.get("audio_file")

        if not audio_file:
            continue

        if start is None or end is None:
            continue

        duration = end - start

        if not is_valid_segment(text, duration):
            continue

        if is_ad(text):  # ✅ strong ad filter
            continue

        filtered.append(r)

    if not filtered:
        print("❌ No usable segments.")
        return []

    # ✅ STEP 2: SORT
    filtered = sorted(filtered, key=lambda x: x["score"])

    # ✅ STEP 3: SELECT
    selected = select_segments(filtered, max_segments)

    blend = []

    # -------------------------
    # 🎬 INTRO
    # -------------------------
    intro = generate_dateline_line("", query=query, stage="intro")

    if intro:
        blend.append({"type": "narration", "text": intro})
        blend.append({"type": "pause", "duration": 0.7})

    # -------------------------
    # 🎬 MAIN FLOW
    # -------------------------
    for i, seg in enumerate(selected):

        text = seg["text"]

        # ✅ ALWAYS INTRODUCE CLIP (FIXED)
        narration = generate_dateline_line("", text, query, stage="segment_intro")

        if narration:
            blend.append({"type": "narration", "text": narration})
            blend.append({"type": "pause", "duration": 0.4})

        # ✅ CLIP
        blend.append({
            "type": "speaker",
            "text": text,
            "audio_file": seg.get("audio_file"),
            "start": seg.get("start"),
            "end": seg.get("end"),
            "source": seg.get("audio_file"),
        })

        blend.append({"type": "pause", "duration": 0.6})

        # ✅ OCCASIONAL BRIDGE
        if i % 2 == 1 and i < len(selected) - 1:
            next_seg = selected[i + 1]

            bridge = generate_dateline_line(
                shorten(text),
                shorten(next_seg["text"]),
                query,
                stage="bridge"
            )

            if bridge:
                blend.append({"type": "narration", "text": bridge})
                blend.append({"type": "pause", "duration": 0.4})

    # -------------------------
    # 🎬 OUTRO
    # -------------------------
    outro = generate_dateline_line("", query=query, stage="outro")

    if outro:
        blend.append({"type": "narration", "text": outro})

    return blend


# =========================
# ✅ TEST
# =========================

if __name__ == "__main__":
    result = build_blend("AI taking jobs")

    print("\n🔥 OUTPUT\n")
    for step in result:
        print(step)












