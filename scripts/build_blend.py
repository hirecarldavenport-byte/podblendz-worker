from scripts.search_faiss import search
from openai import OpenAI
import os
import json
import hashlib  # ✅ NEW

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


def suggest_query(query):
    try:
        with open("topic_patterns.json") as f:
            patterns = json.load(f)

        matches = [p for p in patterns if p in query.lower()]
        return matches[:5] if matches else patterns[:5]

    except Exception:
        return []


# =========================
# ✅ FILTERING
# =========================

def is_strong_sentence(text):
    if not text:
        return False

    text = text.strip()

    if len(text.split()) < 8:
        return False

    if not text[0].isupper():
        return False

    if not text.endswith((".", "?", "!")):
        return False

    bad = ["so ", "and ", "but ", "okay", "well", "you know", "i mean"]

    if any(text.lower().startswith(b) for b in bad):
        return False

    return True


def is_meaningful(text):
    t = text.lower()

    if t.endswith("?"):
        return False

    if len(text.split()) < 10 and any(w in t for w in ["dna", "gene", "genome"]):
        return False

    return True


# ✅ NEW — AD FILTER
def is_ad(text):
    t = text.lower()

    signals = [
        "sponsor",
        "sponsored by",
        "brought to you by",
        "visit",
        ".com",
        "www",
        "sign up",
        "subscribe",
        "promo",
        "use code",
        "support for this podcast"
    ]

    return any(s in t for s in signals)


# ✅ NEW — DEDUP HELPERS
def dedup_key(text):
    cleaned = " ".join(text.lower().split())
    return hashlib.md5(cleaned.encode()).hexdigest()


# =========================
# ✅ DATELINE-STYLE NARRATION
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"""
Act like a calm documentary narrator.

Introduce a deeper idea or mystery about:
{query}

Make it intriguing and controlled.
Max 22 words.
"""

    elif stage == "bridge":
        prompt = f"""
You are guiding a story.

Previous idea:
"{context}"

Next idea:
"{text}"

Do NOT summarize.

Instead, build curiosity or tension.
Max 18 words.
"""

    elif stage == "outro":
        prompt = f"""
Close with a reflective thought about:
{query}

Make it feel unresolved and thought-provoking.
Max 22 words.
"""

    else:
        prompt = f"""
Guide the audience's thinking about this idea:

"{text}"

Add meaning or implication without repeating.
Max 18 words.
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

    selected_pool = []

    seen = set()  # ✅ NEW
    source_counts = {}  # ✅ NEW
    MAX_PER_SOURCE = 3  # ✅ NEW

    for r in results:
        text = r.get("text", "").strip()
        start = r.get("start")
        end = r.get("end")
        source = r.get("audio_file")

        if start is None or end is None:
            continue

        duration = end - start

        if not text or duration < 3:
            continue

        # ✅ REMOVE ADS
        if is_ad(text):
            continue

        # ✅ RELAXED FILTER (keep this from your version)
        if len(text.split()) < 6:
            continue

        # ✅ DEDUP (light)
        key = dedup_key(text)
        if key in seen:
            continue
        seen.add(key)

        # ✅ LIMIT PER SOURCE
        count = source_counts.get(source, 0)
        if count >= MAX_PER_SOURCE:
            continue
        source_counts[source] = count + 1

        selected_pool.append(r)

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    selected_pool = sorted(selected_pool, key=lambda x: x["score"])
    selected = selected_pool[:max_segments]

    if len(selected) < 8:
        selected = selected_pool[:8]

    blend = []

    # -------------------------
    # 🎬 INTRO
    # -------------------------
    intro = generate_dateline_line("", query=query, stage="intro")

    blend.append({
        "type": "narration",
        "text": intro
    })
    blend.append({"type": "pause", "duration": 0.7})

    # -------------------------
    # 🎬 FIRST ENTRY
    # -------------------------
    first = selected[0]

    narration = generate_dateline_line("", first["text"])

    blend.append({"type": "narration", "text": narration})
    blend.append({"type": "pause", "duration": 0.4})

    blend.append({
        "type": "speaker",
        "text": first["text"],
        "audio_file": first.get("audio_file"),
        "start": first.get("start"),
        "end": first.get("end"),
    })

    blend.append({"type": "pause", "duration": 0.6})

    # -------------------------
    # 🎬 MAIN SEQUENCE
    # -------------------------
    for i in range(1, len(selected)):
        prev = selected[i - 1]
        curr = selected[i]

        transition = generate_dateline_line(
            shorten(prev["text"]),
            shorten(curr["text"]),
            query,
            stage="bridge"
        )

        blend.append({"type": "narration", "text": transition})
        blend.append({"type": "pause", "duration": 0.5})

        blend.append({
            "type": "speaker",
            "text": curr["text"],
            "audio_file": curr.get("audio_file"),
            "start": curr.get("start"),
            "end": curr.get("end"),
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
    result = build_blend("CRISPR gene editing")

    print("\n🔥 OUTPUT\n")
    for step in result:
        print(step)














