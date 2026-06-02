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
        "subscribe now"
    ]

    return any(p in t for p in ad_phrases)


# =========================
# ✅ STRONG DEDUP
# =========================

def dedup_key(text):
    cleaned = " ".join(text.lower().split())
    return hashlib.md5(cleaned.encode()).hexdigest()


# =========================
# ✅ DIVERSITY
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

        key = dedup_key(text)
        if key in seen_keys:
            continue

        # limit same podcast domination
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
# ✅ NARRATION (STRONGER GUIDE)
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"""
Speak as a polished podcast host.

Introduce the topic:
{query}

Explain what the listener will learn.

Be clear and engaging.

Max 20 words.
"""

    elif stage == "bridge":
        prompt = f"""
Guide the listener clearly.

Previous idea:
"{context}"

Next idea:
"{text}"

Explain what’s coming next and why it matters.

Max 18 words.
"""

    elif stage == "outro":
        prompt = f"""
Wrap up this episode about:
{query}

Leave the listener with a strong takeaway.

Max 20 words.
"""

    else:
        prompt = f"""
Introduce this segment clearly:

"{text}"

Explain what the listener is about to hear.

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
    # ✅ FILTER CLEANLY
    # -------------------------
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

        if is_ad(text):
            continue

        filtered.append(r)

    if not filtered:
        print("❌ No usable segments.")
        return []

    # -------------------------
    # ✅ SORT
    # -------------------------
    filtered = sorted(filtered, key=lambda x: x["score"])

    # -------------------------
    # ✅ SELECT
    # -------------------------
    selected = select_diverse_segments(filtered, max_segments)

    blend = []

    # -------------------------
    # 🎬 INTRO (STRONG)
    # -------------------------
    intro = generate_dateline_line("", query=query, stage="intro")

    blend.append({"type": "narration", "text": intro})
    blend.append({"type": "pause", "duration": 0.7})

    # -------------------------
    # 🎬 MAIN FLOW (MORE GUIDED)
    # -------------------------
    for i, seg in enumerate(selected):

        text = seg["text"]
        audio_file = seg["audio_file"]

        # ✅ ALWAYS INTRODUCE SEGMENT (KEY FIX)
        narration = generate_dateline_line("", text, query)

        blend.append({"type": "narration", "text": narration})
        blend.append({"type": "pause", "duration": 0.4})

        # ✅ CLIP
        blend.append({
            "type": "speaker",
            "text": text,
            "audio_file": audio_file,
            "start": seg.get("start"),
            "end": seg.get("end"),
            "source": audio_file
        })

        blend.append({"type": "pause", "duration": 0.6})

        # ✅ OCCASIONAL TRANSITION
        if i % 2 == 1:
            bridge = generate_dateline_line(
                shorten(text),
                shorten(selected[i]["text"]),
                query,
                stage="bridge"
            )

            blend.append({"type": "narration", "text": bridge})
            blend.append({"type": "pause", "duration": 0.4})

    # -------------------------
    # 🎬 OUTRO
    # -------------------------
    outro = generate_dateline_line("", query=query, stage="outro")

    blend.append({"type": "narration", "text": outro})

    return blend












