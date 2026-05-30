from search_faiss import search
from openai import OpenAI
import os
import random

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ shorten long segments for GPT clarity
def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


# ✅ NEW: stronger semantic quality filter
def is_strong_sentence(text):
    if not text:
        return False

    text = text.strip()
    words = text.split()

    if len(words) < 8:
        return False

    # avoid mid-fragment starts
    if text[0].islower():
        return False

    # prefer complete sentences
    if not text.endswith((".", "?", "!")):
        return False

    return True


# ✅ FINAL NARRATION ENGINE (IMPROVED)
def generate_narration(prev_text, next_text, query, position="middle", style_hint=None):

    if position == "intro":
        prompt = f"""
Start mid-thought.

Topic: {query}

Make one grounded observation.
Avoid repeating key topic words.
No general life advice.

Max 22 words.
"""

    elif position == "outro":
        prompt = f"""
End with an unresolved thought.

Topic: {query}

Do not summarize.
Leave tension or open possibility.

Max 22 words.
"""

    else:
        prompt = f"""
You are noticing a meaningful relationship between two ideas.

Topic: {query}

Previous idea:
"{prev_text}"

Next idea:
"{next_text}"

Instructions:
- Highlight a specific contrast or tension
- Avoid repeating core topic words
- Avoid phrases like "the tension lies"
- Do NOT generalize
- Do NOT give advice
- Keep it grounded and specific

Style: {style_hint}

Max 16 words.
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

    # ✅ DEBUG: raw results
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

    # ✅ correct FAISS sort (lower score = better)
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], -x["score"]),
        reverse=True
    )

    # ✅ structure-aware ordering (replaces full shuffle)
    candidates = selected_pool[:max_segments * 5]
    candidates = sorted(candidates, key=lambda x: x["score"])

    # small local shuffle for natural variation
    for i in range(0, len(candidates), 3):
        chunk = candidates[i:i+3]
        random.shuffle(chunk)
        candidates[i:i+3] = chunk

    selected = []
    source_counts = {}

    for r in candidates:
        source = r.get("source", "")
        parts = source.split("/")
        source_key = parts[2] if len(parts) > 2 else source

        count = source_counts.get(source_key, 0)

        # strong diversity early, flexible later
        if count < 1:
            selected.append(r)
            source_counts[source_key] = count + 1
        elif len(selected) < max_segments:
            selected.append(r)

        if len(selected) >= max_segments:
            break

    # ✅ DEBUG: selected segments
    print("\n✅ SELECTED SEGMENTS:\n")
    for i, s in enumerate(selected):
        print(f"{i+1}. {s['text'][:120]}")
        print(f"   Source: {s['source']}")
        print(f"   Relevance: {s['relevance']} | Score: {s['score']}\n")

    blend = []

    # ✅ intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

    styles = [
        "observational",
        "contrast-driven",
        "subtle",
        "unexpected",
        "minimal",
        "grounded"
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
                prev_text=shorten(seg["text"]),
                next_text=shorten(nxt["text"]),
                query=query,
                style_hint=styles[i % len(styles)]
            )

            blend.append({
                "type": "narration",
                "text": transition
            })

    # ✅ outro
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







