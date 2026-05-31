from search_faiss import search
from openai import OpenAI
import os

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


def is_strong_sentence(text):
    if not text:
        return False

    text = text.strip()
    words = text.split()

    if len(words) < 8:
        return False

    if not text[0].isupper():
        return False

    if not text.endswith((".", "?", "!")):
        return False

    bad_starts = ["so ", "and ", "but ", "okay", "well", "you know", "i mean"]
    if any(text.lower().startswith(b) for b in bad_starts):
        return False

    if any(p in text.lower() for p in ["is just", "is basically", "it's just"]):
        return False

    return True


def is_meaningful(text):
    t = text.lower()

    if t.endswith("?"):
        return False

    if len(text.split()) < 10 and any(w in t for w in ["dna", "gene", "genome"]):
        return False

    weak = ["what", "how", "why", "can you", "do you"]
    if sum(1 for w in weak if w in t) > 0 and len(text.split()) < 12:
        return False

    return True


def categorize_segment(text):
    t = text.lower()

    if any(w in t for w in ["fear", "uncertainty", "risk", "start"]):
        return "setup"

    elif any(w in t for w in ["habit", "decision", "process", "system"]):
        return "middle"

    else:
        return "end"


# =========================
# ✅ NARRATION
# =========================

def generate_narration(prev_text, next_text, query, position="middle"):

    if position == "intro":
        prompt = f"""
Start mid-thought about: {query}

Make it sound like an ongoing conversation.

Max 18 words.
"""

    elif position == "outro":
        prompt = f"""
End with a thought that lingers about: {query}

Do not summarize.

Max 18 words.
"""

    else:
        prompt = f"""
Notice something subtle between these two:

"{prev_text}"
"{next_text}"

No explaining. No summarizing.

Max 14 words.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return safe_content(response)


# =========================
# ✅ MAIN
# =========================

def build_blend(query, max_segments=16):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    if not results:
        print("❌ No results found.")
        return []

    selected_pool = []

    for r in results:
        text = r.get("text", "").strip()
        start, end = r.get("start"), r.get("end")

        duration = (end - start) if (start and end) else 0

        if not text or duration < 3:
            continue

        if not is_strong_sentence(text) or not is_meaningful(text):
            continue

        selected_pool.append(r)

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    selected_pool = sorted(selected_pool, key=lambda x: x["score"])
    candidates = selected_pool[:max_segments * 5]

    setup, middle, end = [], [], []

    for r in candidates:
        cat = categorize_segment(r["text"])
        (setup if cat == "setup" else middle if cat == "middle" else end).append(r)

    selected = setup[:4] + middle[:6] + end[:max_segments]

    selected = sorted(selected, key=lambda x: x["score"])

    LOW = len(selected) < int(max_segments * 0.6)

    blend = []

    # ✅ intro
    intro = (
        "There is limited direct discussion on this topic, but some ideas begin to connect."
        if LOW else generate_narration("", "", query, "intro")
    )

    blend.append({"type": "narration", "text": intro})
    blend.append({"type": "pause", "duration": 0.5})

    for i, seg in enumerate(selected):

        blend.append({"type": "clip", **seg})
        blend.append({"type": "pause", "duration": 0.4})

        if LOW and i == 1:
            blend.append({
                "type": "narration",
                "text": "There are fewer direct discussions, but some surrounding ideas still connect."
            })

        if i < len(selected) - 1:
            nxt = selected[i + 1]

            transition = generate_narration(
                shorten(seg["text"]),
                shorten(nxt["text"]),
                query
            )

            blend.append({"type": "narration", "text": transition})
            blend.append({"type": "pause", "duration": 0.5})

    # ✅ outro
    outro = (
        "Try broadening the topic for deeper exploration."
        if LOW else generate_narration("", "", query, "outro")
    )

    blend.append({"type": "narration", "text": outro})

    return blend


if __name__ == "__main__":
    blend = build_blend("CRISPR gene editing")

    print("\n🔥 OUTPUT\n")
    for step in blend:
        print(step)









