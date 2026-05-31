from search_faiss import search
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# =========================
# ✅ TEXT HELPERS
# =========================

def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


# ✅ Strong structure filter
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

    # remove filler speech
    bad_starts = [
        "so ", "and ", "but ", "okay", "well",
        "you know", "i mean"
    ]

    for b in bad_starts:
        if text.lower().startswith(b):
            return False

    # remove bland phrasing
    bland = [
        "is just", "is basically", "it's just", "these are"
    ]

    for b in bland:
        if b in text.lower():
            return False

    return True


# ✅ Meaning filter (BIG IMPROVEMENT)
def is_meaningful(text):
    text_lower = text.lower()

    # avoid question fragments
    if text_lower.endswith("?"):
        return False

    # avoid vague fragments
    weak_patterns = [
        "what", "how", "why", "can you", "do you"
    ]

    if sum(1 for w in weak_patterns if w in text_lower) > 0 and len(text.split()) < 12:
        return False

    # avoid technical fragments without context
    if len(text.split()) < 10 and any(w in text_lower for w in ["gene", "dna", "genome"]):
        return False

    return True


# =========================
# ✅ NARRATIVE STRUCTURE
# =========================

def categorize_segment(text):
    t = text.lower()

    if any(w in t for w in ["fear", "uncertainty", "start", "begin"]):
        return "setup"

    elif any(w in t for w in ["habit", "decision", "process", "system", "discipline"]):
        return "middle"

    else:
        return "end"


# =========================
# ✅ NARRATION ENGINE
# =========================

def generate_narration(prev_text, next_text, query, position="middle", style_hint=None):

    if position == "intro":
        prompt = f"""
Start mid-thought.

Topic: {query}

Make a specific observation about how people engage with this idea.
Make it feel like a real conversation already in progress.

Max 18 words.
"""

    elif position == "outro":
        prompt = f"""
End with a thought that lingers.

Topic: {query}

Do not summarize.
Slightly reframe what came before.

Max 18 words.
"""

    else:
        prompt = f"""
You are noticing something subtle between two ideas.

Topic: {query}

Previous:
"{prev_text}"

Next:
"{next_text}"

Instructions:
- Do NOT explain
- Do NOT summarize
- Avoid repeating patterns
- Avoid words like "contrast", "difference", "tension"
- Say something specific and slightly unexpected

Style: {style_hint}

Max 14 words.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    if not response or not response.choices:
        return ""

    content = response.choices[0].message.content
    return content.strip() if content else ""


# =========================
# ✅ MAIN BUILDER
# =========================

def build_blend(query, max_segments=16):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=100) or []

    if not results:
        print("❌ No results found.")
        return []

    # ✅ DEBUG RAW
    print("\n🔎 RAW SEARCH RESULTS (Top 10):\n")
    for i, r in enumerate(results[:10]):
        print(f"{i+1}. {r['text'][:120]}")
        print(f"   Source: {r['source']}")
        print(f"   Score: {r['score']}\n")

    selected_pool = []

    for r in results:
        text = r.get("text", "").strip()

        start = r.get("start")
        end = r.get("end")
        duration = (end - start) if (start is not None and end is not None) else 0

        if (
            not text
            or duration < 3
            or not is_strong_sentence(text)
            or not is_meaningful(text)
        ):
            continue

        selected_pool.append(r)

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    # ✅ FAISS sort
    selected_pool = sorted(selected_pool, key=lambda x: x["score"])

    candidates = selected_pool[:max_segments * 5]

    # ✅ categorize
    setup, middle, end = [], [], []

    for r in candidates:
        cat = categorize_segment(r["text"])

        if cat == "setup":
            setup.append(r)
        elif cat == "middle":
            middle.append(r)
        else:
            end.append(r)

    # ✅ structured selection
    selected = []
    selected += setup[:4]
    selected += middle[:6]

    remaining = max_segments - len(selected)
    selected += end[:remaining]

    # ✅ diversity
    final_selected = []
    source_counts = {}

    for r in selected:
        source = r.get("source", "")
        source_key = source.split("/")[2] if "/" in source else source

        count = source_counts.get(source_key, 0)

        if count < 2 or len(final_selected) < 5:
            final_selected.append(r)
            source_counts[source_key] = count + 1

    selected = final_selected

    # ✅ prioritize best opening
    selected = sorted(selected, key=lambda x: x["score"])

    # ✅ DEBUG SELECTED
    print("\n✅ SELECTED SEGMENTS:\n")
    for i, s in enumerate(selected):
        print(f"{i+1}. {s['text'][:120]}")
        print(f"   Source: {s['source']}")
        print(f"   Score: {s['score']}\n")

    # =========================
    # ✅ BUILD FINAL BLEND
    # =========================

    blend = []

    # intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })
    blend.append({"type": "pause", "duration": 0.5})

    styles = ["natural", "subtle", "curious", "observational", "reflective"]

    for i, seg in enumerate(selected):

        blend.append({
            "type": "clip",
            "text": seg["text"],
            "start": seg["start"],
            "end": seg["end"],
            "source": seg["source"]
        })

        blend.append({"type": "pause", "duration": 0.4})

        if i < len(selected) - 1:
            nxt = selected[i + 1]

            transition = generate_narration(
                shorten(seg["text"]),
                shorten(nxt["text"]),
                query,
                style_hint=styles[i % len(styles)]
            )

            blend.append({
                "type": "narration",
                "text": transition
            })

            blend.append({"type": "pause", "duration": 0.5})

    # outro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="outro")
    })

    return blend


# =========================
# ✅ RUN
# =========================

if __name__ == "__main__":
    blend = build_blend("CRISPR gene editing")

    print("\n🔥 BLEND OUTPUT:\n")

    for step in blend:
        print(step)







