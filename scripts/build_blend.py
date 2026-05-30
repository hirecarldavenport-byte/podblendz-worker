from search_test import search
from openai import OpenAI
import os

# ✅ OpenAI client
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ ✅ AI Narration Generator (MULTI-PERSPECTIVE AWARE)
def generate_narration(prev_text, next_text, query, position="middle"):
    if position == "intro":
        prompt = f"""
Create a compelling intro for a guided audio experience.

Topic: {query}

This experience blends ideas from multiple perspectives.

Make it reflective, engaging, and natural (2–3 sentences).
Do NOT sound like one person explaining everything.
"""

    elif position == "outro":
        prompt = f"""
Create a thoughtful closing reflection.

Topic: {query}

You have explored multiple perspectives.

Synthesize them into a meaningful takeaway (2–3 sentences).
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
- Treat these as different viewpoints
- Highlight contrast or expansion
- Do NOT sound like one continuous speaker

Write a short, natural transition (1–2 sentences).
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
def build_blend(query, max_segments=10):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query) or []

    if not results:
        print("❌ No results found.")
        return []

    KEYWORDS = ["fail", "failure", "mistake", "growth", "change", "identity", "learn", "struggle"]

    selected_pool = []

    # ✅ Step 1 — Lightweight filtering + scoring
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

    # ✅ Step 2 — Sort by relevance + similarity
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], x["score"]),
        reverse=True
    )

    # ✅ Step 3 — Create candidate pool
    candidates = selected_pool[:max_segments * 4]

    # ✅ Step 4 — Enforce source diversity
    selected = []
    source_counts = {}

    for r in candidates:
        source = r.get("source") or ""

        # ✅ Extract high-level source (podcast/channel)
        parts = source.split("/")
        source_key = parts[2] if len(parts) > 2 else source

        count = source_counts.get(source_key, 0)

        # ✅ Limit per source (changeable later)
        if count >= 2:
            continue

        selected.append(r)
        source_counts[source_key] = count + 1

        if len(selected) >= max_segments:
            break

    if not selected:
        print("❌ No segments selected after diversity filtering.")
        return []

    # ✅ Step 5 — Build Blend with AI narration
    blend = []

    # ✅ Intro
    intro_text = generate_narration("", "", query, position="intro")

    blend.append({
        "type": "narration",
        "text": intro_text
    })

    # ✅ Main flow
    for i, segment in enumerate(selected):

        # ✅ Clip
        blend.append({
            "type": "clip",
            "text": segment["text"],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "source": segment.get("source")
        })

        # ✅ Transition
        if i < len(selected) - 1:
            next_seg = selected[i + 1]

            transition_text = generate_narration(
                prev_text=f"[Perspective A] {segment['text']}",
                next_text=f"[Perspective B] {next_seg['text']}",
                query=query
            )

            blend.append({
                "type": "narration",
                "text": transition_text
            })

    # ✅ Outro
    outro_text = generate_narration("", "", query, position="outro")

    blend.append({
        "type": "narration",
        "text": outro_text
    })

    return blend


# ✅ ✅ RUN TEST
if __name__ == "__main__":
    blend = build_blend("reinventing yourself after failure")

    print("\n🔥 BLEND OUTPUT:\n")

    if not blend:
        print("No blend generated.")
    else:
        for step in blend:
            print(step)


