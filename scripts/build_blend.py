from search_faiss import search
from openai import OpenAI
import os
import random

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


# ✅ FINAL NARRATION ENGINE
def generate_narration(prev_text, next_text, query, position="middle", style_hint=None):

    if position == "intro":
        prompt = f"""
Start in the middle of a thoughtful conversation.

Topic: {query}

Make one specific observation. No "welcome" language.

Max 22 words.
"""

    elif position == "outro":
        prompt = f"""
Offer a closing thought.

Topic: {query}

Leave a lingering idea. No summary.

Max 22 words.
"""

    else:
        prompt = f"""
You are noticing patterns.

Topic: {query}

Previous idea:
"{prev_text}"

Next idea:
"{next_text}"

- No advice
- No resolution
- Be specific
- Stay observational

Style hint: {style_hint}

Max 16 words.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    if not response or not response.choices:
        return ""

    content = response.choices[0].message.content

    if not content:
       return ""

    return content.strip()



# ✅ MAIN BUILDER
def build_blend(query, max_segments=16):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=100)

    if not results:
        print("❌ No results found.")
        return []

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

        duration = (end - start) if (start and end) else 0

        if not text or len(text) < 25 or duration < 3:
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

    # ✅ CORRECT FAISS SORT
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], -x["score"]),
        reverse=True
    )

    # ✅ shuffle for natural flow
    candidates = selected_pool[:max_segments * 5]
    random.shuffle(candidates)

    selected = []
    source_counts = {}

    for r in candidates:
        source = r.get("source", "")
        source_key = source.split("/")[2] if "/" in source else source

        count = source_counts.get(source_key, 0)

        if count < 1:
            selected.append(r)
            source_counts[source_key] = count + 1

        if len(selected) >= max_segments:
            break

    blend = []

    # ✅ intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

    styles = [
        "reflective",
        "conversational",
        "contrast",
        "subtle",
        "unexpected",
        "simple"
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


if __name__ == "__main__":
    blend = build_blend("fear vs courage in decision making")

    print("\n🔥 BLEND OUTPUT:\n")

    for step in blend:
        print(step)






