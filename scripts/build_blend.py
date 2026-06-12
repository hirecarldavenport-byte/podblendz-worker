from scripts.search_faiss import search
from openai import OpenAI
import os
import json
import hashlib

# ✅ INIT
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
    except Exception as e:
        print("⚠️ safe_content error:", str(e))
        return ""


def suggest_query(query):
    try:
        with open("topic_patterns.json") as f:
            patterns = json.load(f)

        matches = [p for p in patterns if p in query.lower()]
        return matches[:5] if matches else patterns[:5]

    except Exception as e:
        print("⚠️ suggest_query error:", str(e))
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


def is_ad(text):
    t = text.lower()

    signals = [
        "sponsor",
        "sponsored",
        "brought to you",
        "this episode is brought",
        "support for",
        "advertising",
        "promo",
        "promotion",
        "partner",
        "visit",
        ".com",
        "www",
        "sign up",
        "subscribe",
        "use code",
        "dot com",
        "offer",
        "free trial"
    ]

    return any(s in t for s in signals)


def dedup_key(text):
    words = text.lower().split()
    core = " ".join(words[:12])
    return hashlib.md5(core.encode()).hexdigest()


def extract_show_name(source_path):
    try:
        parts = source_path.split("/")
        if len(parts) > 2:
            return parts[-2].replace("_", " ").title()
    except:
        pass
    return "this podcast"


# =========================
# ✅ DATELINE-STYLE NARRATION
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"""
Act like a calm documentary narrator.

Introduce a deeper idea about:
{query}

Max 22 words.
"""

    elif stage == "bridge":
        prompt = f"""
Previous idea:
"{context}"

Next idea:
"{text}"

Build curiosity. Do NOT summarize.
Max 18 words.
"""

    elif stage == "outro":
        prompt = f"""
Close with a reflective thought about:
{query}

Max 22 words.
"""

    else:
        prompt = f"""
Guide the audience's thinking about:

"{text}"

Max 18 words.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return safe_content(response)

    except Exception as e:
        print("⚠️ GPT error:", str(e))
        return ""


# =========================
# ✅ MAIN BUILDER
# =========================

def build_blend(query, max_segments=20):

    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    selected_pool = []

    seen = set()
    source_counts = {}

    skipped_missing_audio = 0

    MAX_PER_SOURCE = 2

    for r in results:

        text = r.get("text", "").strip()
        start = r.get("start")
        end = r.get("end")
        source = r.get("audio_file")

        # ✅ CRITICAL FIX
        if not source:
            skipped_missing_audio += 1
            continue

        if start is None or end is None:
            continue

        duration = end - start

        if not text or duration < 3:
            continue

        if is_ad(text):
            continue

        if len(text.split()) < 6:
            continue

        key = dedup_key(text)
        if key in seen:
            continue
        seen.add(key)

        count = source_counts.get(source, 0)
        if count >= MAX_PER_SOURCE:
            continue

        source_counts[source] = count + 1

        selected_pool.append(r)

    print(f"✅ Retrieved {len(selected_pool)} usable segments")
    print(f"⚠️ Skipped {skipped_missing_audio} segments missing audio_file")

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    selected_pool = sorted(selected_pool, key=lambda x: x["score"])
    selected = selected_pool[:max_segments]

    if len(selected) < 8:
        selected = selected_pool[:8]

    print(f"✅ Final selection: {len(selected)} segments")

    blend = []

    # =========================
    # 🎬 INTRO
    # =========================

    intro = generate_dateline_line("", query=query, stage="intro")

    blend.append({"type": "narration", "text": intro})
    blend.append({"type": "pause", "duration": 0.7})

    # =========================
    # 🎬 FIRST ENTRY
    # =========================

    first = selected[0]
    show_name = extract_show_name(first.get("audio_file", ""))

    narration = f"From {show_name}. {generate_dateline_line('', first['text'])}"

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

    # =========================
    # 🎬 MAIN SEQUENCE
    # =========================

    for i in range(1, len(selected)):

        prev = selected[i - 1]
        curr = selected[i]

        show_name = extract_show_name(curr.get("audio_file", ""))

        transition = generate_dateline_line(
            shorten(prev["text"]),
            shorten(curr["text"]),
            query,
            stage="bridge"
        )

        blend.append({"type": "narration", "text": transition})
        blend.append({"type": "pause", "duration": 0.3})

        blend.append({"type": "narration", "text": f"From {show_name}."})
        blend.append({"type": "pause", "duration": 0.3})

        blend.append({
            "type": "speaker",
            "text": curr["text"],
            "audio_file": curr.get("audio_file"),
            "start": curr.get("start"),
            "end": curr.get("end"),
        })

        blend.append({"type": "pause", "duration": 0.6})

    # =========================
    # 🎬 OUTRO
    # =========================

    outro = generate_dateline_line("", query=query, stage="outro")

    blend.append({"type": "narration", "text": outro})

    print(f"✅ Built blend with {len(blend)} steps")

    return blend


# =========================
# ✅ TEST (ONLY BUILDS STRUCTURE)
# =========================

if __name__ == "__main__":

    query = "CRISPR gene editing"

    result = build_blend(query)

    print("\n🔥 OUTPUT\n")
    for step in result:
        print(step)















