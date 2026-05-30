from search_test import search
from openai import OpenAI
import os
import random

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ ✅ NATURAL, INTELLIGENT NARRATION
def generate_narration(prev_text, next_text, query, position="middle", style_hint=None):

    if position == "intro":
        prompt = f"""
You are a thoughtful podcast host guiding a listener through ideas.

Topic: {query}

Set up the exploration in a clear, natural, engaging way.
Avoid sounding academic or overly motivational.

Max 25 words.
"""

    elif position == "outro":
        prompt = f"""
Offer a closing reflection.

Topic: {query}

Do NOT summarize everything.
Leave the listener with a thought or question.

Keep it simple and natural.

Max 25 words.
"""

    else:
        prompt = f"""
You are guiding a listener through different perspectives.

Topic: {query}

Previous idea:
"{prev_text}"

Next idea:
"{next_text}"

Instructions:
- Connect or contrast the ideas
- Keep language natural and conversational
- Avoid repetitive phrasing about failure/growth
- Vary how you speak (observation, question, contrast)

Style hint: {style_hint}

Max 18 words.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    if not response or not response.choices:
        return ""

    content = response.choices[0].message.content
    return content.strip() if content else ""


# ✅ ✅ MAIN BLEND BUILDER
def build_blend(query, max_segments=12):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query) or []

    if not results:
        print("❌ No results found.")
        return []

    KEYWORDS = [
        "fail", "failure", "mistake", "growth", "change",
        "identity", "learn", "struggle", "success",
        "risk", "reinvent", "adapt"
    ]

    selected_pool = []

    # ✅ Step 1 — Filter + score
    for r in results:
        text = r.get("text", "").strip()
        text_lower = text.lower()

        start = r.get("start")
        end = r.get("end")

        duration = (end - start) if (start is not None and end is not None) else 0

        if (
            not text
            or len(text) < 35
            or len(text.split()) < 6
            or duration < 5
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

    # ✅ Step 2 — Deduplicate
    seen_texts = set()
    unique_pool = []

    for r in selected_pool:
        t = r.get("text")
        if t not in seen_texts:
            seen_texts.add(t)
            unique_pool.append(r)

    selected_pool = unique_pool

    # ✅ Step 3 — Sort
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], x["score"]),
        reverse=True
    )

    # ✅ Step 4 — Candidate pool
    candidates = selected_pool[:max_segments * 5]

    # ✅ Step 5 — Soft diversity
    selected = []
    source_counts = {}

    for r in candidates:
        source = r.get("source") or ""
        parts = source.split("/")
        source_key = parts[2] if len(parts) > 2 else source

        count = source_counts.get(source_key, 0)

        if count < 2:
            selected.append(r)
            source_counts[source_key] = count + 1
        elif len(selected) < max_segments:
            selected.append(r)

        if len(selected) >= max_segments:
            break

    if len(selected) < max_segments:
        print(f"⚠️ Only {len(selected)} segments selected")

    # ✅ Step 6 — Build blend
    blend = []

    # ✅ Intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

    # ✅ Style rotation (critical improvement)
    style_options = [
        "make it reflective",
        "make it slightly conversational",
        "frame it as a question",
        "highlight contrast",
        "keep it simple",
        "point out something unexpected"
    ]

    # ✅ Flow
    for i, segment in enumerate(selected):

        blend.append({
            "type": "clip",
            "text": segment["text"],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "source": segment.get("source")
        })

        if i < len(selected) - 1:
            next_seg = selected[i + 1]

            style_hint = style_options[i % len(style_options)]

            transition = generate_narration(
                prev_text=segment["text"],
                next_text=next_seg["text"],
                query=query,
                style_hint=style_hint
            )

            blend.append({
                "type": "narration",
                "text": transition
            })

    # ✅ Outro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="outro")
    })

    return blend


# ✅ ✅ RUN
if __name__ == "__main__":
    blend = build_blend("reinventing yourself after failure")

    print("\n🔥 BLEND OUTPUT:\n")

    if not blend:
        print("No blend generated.")
    else:
        for step in blend:
            print(step)




