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
    if not text:
        return False

    if len(text.split()) < 6:
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
        "support for this podcast"
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

def select_diverse_segments(results, max_segments=12):
    selected = []
    seen_keys = set()
    seen_sources = {}

    MAX_PER_SOURCE = 3

    for r in results:
        text = r.get("text", "").strip()
        audio_file = r.get("audio_file")

        if not text or not audio_file:
            continue

        # ✅ dedup
        key = dedup_key(text)
        if key in seen_keys:
            continue

        # ✅ source balancing
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
# ✅ DATELINE NARRATION
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"""
Speak like a polished podcast host.

Introduce the topic:
{query}

Explain what the listener will gain.

Max 20 words.
"""

    elif stage == "bridge":
        prompt = f"""
Guide the listener.

Previous idea:
"{context}"

Next idea:
"{text}"

Explain the transition clearly.

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
Provide context for this idea:

"{text}"

Help the listener understand why it matters.

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

def build_blend(query, max_segments=12):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    # -------------------------
    # ✅ STEP 1: CLEAN FILTERING
    # -------------------------
    filtered = []

    for r in results:
        text = r.get("text", "").strip()
        start = r.get("start")
        end = r.get("end")
        audio_file = r.get("audio_file")

        # ✅ must have audio
        if not audio_file:
            continue

        if start is None or end is None:
            continue

        duration = end - start

        if not is_valid_segment(text, duration):
            continue

        if is_ad(text):  # ✅ remove ads
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
        audio_file = seg["audio_file"]

        # ✅ controlled narration
        if i == 0:
            narration = generate_dateline_line("", text, query)

            blend.append({"type": "narration", "text": narration})
            blend.append({"type": "pause", "duration": 0.4})

        elif i % 2 == 0:
            prev = selected[i - 1]

            narration = generate_dateline_line(
                shorten(prev["text"]),
                shorten(text),
                query,
                stage="bridge"
            )

            blend.append({"type": "narration", "text": narration})
            blend.append({"type": "pause", "duration": 0.4})

        # ✅ speaker
        blend.append({
            "type": "speaker",
            "text": text,
            "audio_file": audio_file,
            "start": seg.get("start"),
            "end": seg.get("end"),
            "source": audio_file
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
    result = build_blend("AI taking jobs")

    print("\n🔥 OUTPUT\n")
    for step in result:
        print(step)











