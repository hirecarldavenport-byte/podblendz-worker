from search_faiss import search
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ shorten long clips for narration clarity
def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


# ✅ strong clip filter (important for audio quality)
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

    # ❌ remove conversational filler
    bad_starts = [
        "so ", "and ", "but ", "okay", "well",
        "you know", "i mean"
    ]

    for b in bad_starts:
        if text.lower().startswith(b):
            return False

    return True


# ✅ narrative grouping (for story flow)
def categorize_segment(text):
    t = text.lower()

    if any(w in t for w in ["fear", "uncertainty", "anxiety"]):
        return "setup"

    elif any(w in t for w in ["decision", "habit", "risk", "process", "system"]):
        return "middle"

    else:
        return "end"


# ✅ narration engine (TTS-optimized)
def generate_narration(prev_text, next_text, query, position="middle", style_hint=None):

    if position == "intro":
        prompt = f"""
Start mid-thought.

Topic: {query}

Make a grounded observation about how people behave.
Avoid general life advice.

Max 20 words.
"""

    elif position == "outro":
        prompt = f"""
End with a thought that lingers.

Topic: {query}

Do not summarize.
Slightly reframe everything said before.

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
- Avoid repeating topic words
- Avoid patterns like "the tension lies"
- Just describe what is interesting or revealing

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


# ✅ MAIN BUILDER
def build_blend(query, max_segments=16):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=100) or []

    if not results:
        print("❌ No results found.")
        return []

    # ✅ DEBUG — RAW
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

        if not text or duration < 3 or not is_strong_sentence(text):
            continue

        selected_pool.append(r)

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    # ✅ sort FAISS (lower score = better)
    selected_pool = sorted(selected_pool, key=lambda x: x["score"])

    candidates = selected_pool[:max_segments * 5]

    # ✅ categorize into narrative phases
    setup, middle, end = [], [], []

    for r in candidates:
        cat = categorize_segment(r["text"])

        if cat == "setup":
            setup.append(r)
        elif cat == "middle":
            middle.append(r)
        else:
            end.append(r)

    # ✅ build structured story
    selected = []
    selected += setup[:4]
    selected += middle[:6]

    remaining = max_segments - len(selected)
    selected += end[:remaining]

    # ✅ enforce diversity (important)
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

    # ✅ DEBUG — SELECTED
    print("\n✅ SELECTED SEGMENTS:\n")
    for i, s in enumerate(selected):
        print(f"{i+1}. {s['text'][:120]}")
        print(f"   Source: {s['source']}")
        print(f"   Score: {s['score']}\n")

    # ✅ BUILD BLEND (TTS READY)
    blend = []

    # ✅ intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

    blend.append({"type": "pause", "duration": 0.5})

    styles = ["natural", "observational", "subtle", "curious", "reflective"]

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

    # ✅ outro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="outro")
    })

    return blend


# ✅ RUN
if __name__ == "__main__":
    blend = build_blend("Reading Books")

    print("\n🔥 BLEND OUTPUT:\n")

    for step in blend:
        print(step)







