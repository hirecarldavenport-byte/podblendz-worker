from search_faiss import search
from openai import OpenAI
import os
import random

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ shorten for better narration clarity
def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


# ✅ strong sentence filter (prevents bad audio clips)
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

    return True


# ✅ categorize for narrative arc
def categorize_segment(text):
    t = text.lower()

    if any(w in t for w in ["fear", "uncertainty", "anxiety"]):
        return "setup"

    elif any(w in t for w in ["decision", "risk", "process", "system"]):
        return "middle"

    else:
        return "end"


# ✅ narration engine (TTS-friendly)
def generate_narration(prev_text, next_text, query, position="middle", style_hint=None):

    if position == "intro":
        prompt = f"""
Start mid-thought.

Topic: {query}

Make a grounded observation about how people behave under uncertainty.
Avoid abstract philosophy.

Max 20 words.
"""

    elif position == "outro":
        prompt = f"""
Close with an open-ended reflection.

Topic: {query}

Do not summarize.
Leave something unresolved.

Max 20 words.
"""

    else:
        prompt = f"""
You are noticing a connection between two ideas.

Topic: {query}

Previous:
"{prev_text}"

Next:
"{next_text}"

Instructions:
- Highlight a specific contrast or shift
- Avoid repeating the topic words
- Avoid phrases like "the tension lies"
- No advice
- Keep it natural and conversational

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

    KEYWORDS = [
        "fail", "failure", "mistake", "growth",
        "change", "identity", "learn",
        "struggle", "success", "risk"
    ]

    selected_pool = []

    for r in results:
        text = r.get("text", "").strip()
        text_lower = text.lower()

        start = r.get("start")
        end = r.get("end")

        duration = (end - start) if (start is not None and end is not None) else 0

        if (
            not text
            or len(text) < 25
            or duration < 3
            or not is_strong_sentence(text)
        ):
            continue

        relevance = sum(1 for k in KEYWORDS if k in text_lower)

        selected_pool.append({
            **r,
            "relevance": relevance
        })

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    # ✅ dedupe
    seen = set()
    unique_pool = []
    for r in selected_pool:
        if r["text"] not in seen:
            seen.add(r["text"])
            unique_pool.append(r)

    selected_pool = unique_pool

    # ✅ correct FAISS ordering
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], -x["score"]),
        reverse=True
    )

    # ✅ candidate pool
    candidates = selected_pool[:max_segments * 5]

    # ✅ categorize for flow
    setup, middle, end = [], [], []

    for r in candidates:
        cat = categorize_segment(r["text"])

        if cat == "setup":
            setup.append(r)
        elif cat == "middle":
            middle.append(r)
        else:
            end.append(r)

    # ✅ build structured narrative
    selected = []

    selected += setup[:4]
    selected += middle[:6]

    remaining = max_segments - len(selected)
    selected += end[:remaining]

    # ✅ enforce diversity
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

    # ✅ BUILD BLEND
    blend = []

    # Intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

    styles = [
        "natural",
        "observational",
        "contrast",
        "subtle",
        "curious",
        "minimal"
    ]

    for i, seg in enumerate(selected):

        blend.append({
            "type": "clip",
            "text": seg["text"],
            "start": seg.get("start"),
            "end": seg.get("end"),
            "source": seg.get("source")
        })

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

    # Outro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="outro")
    })

    return blend


# ✅ RUN
if __name__ == "__main__":
    blend = build_blend("fear vs courage in decision making")

    print("\n🔥 BLEND OUTPUT:\n")

    for step in blend:
        print(step)







