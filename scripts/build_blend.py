from search_test import search
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def generate_narration(prev_text, next_text, query, position="middle"):
    """
    Generate contextual narration using AI
    """

    if position == "intro":
        prompt = f"""
Create a compelling intro for a guided audio experience.

Topic: {query}

Make it reflective, engaging, and concise (2-3 sentences).
"""
    elif position == "outro":
        prompt = f"""
Create a thoughtful closing reflection for a guided audio experience.

Topic: {query}

End with a sense of insight or perspective (2-3 sentences).
"""
    else:
        prompt = f"""
You are guiding someone through a set of ideas.

Topic: {query}

Previous idea:
"{prev_text}"

Next idea:
"{next_text}"

Write a natural, thoughtful transition (1-2 sentences) that connects the ideas.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content
    return content.strip() if content else ""


def build_blend(query, max_segments=10):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query) or []

    if not results:
        print("❌ No results found.")
        return []

    selected_pool = []

    KEYWORDS = ["fail", "failure", "mistake", "growth", "change", "identity", "learn", "struggle"]

    # ✅ Step 1: Light filtering + scoring
    for r in results:
        text = r.get("text", "").strip()
        text_lower = text.lower()

        start = r.get("start")
        end = r.get("end")

        duration = 0
        if start is not None and end is not None:
            duration = end - start

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

    # ✅ Step 2: Sort by relevance + semantic score
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], x["score"]),
        reverse=True
    )

    # ✅ Step 3: Create selection pool
    selected_candidates = selected_pool[:max_segments * 3]

    # ✅ Step 4: Final selection
    selected = selected_candidates[:max_segments]

    # ✅ Step 5: Build blend with AI narration
    blend = []

    # ✅ Intro (AI)
    intro_text = generate_narration("", "", query, position="intro")

    blend.append({
        "type": "narration",
        "text": intro_text
    })

    # ✅ Main flow
    for i, segment in enumerate(selected):

        # Clip
        blend.append({
            "type": "clip",
            "text": segment["text"],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "source": segment.get("source")
        })

        # Transition
        if i < len(selected) - 1:
            next_seg = selected[i + 1]

            transition_text = generate_narration(
                prev_text=segment["text"],
                next_text=next_seg["text"],
                query=query
            )

            blend.append({
                "type": "narration",
                "text": transition_text
            })

    # ✅ Outro (AI)
    outro_text = generate_narration("", "", query, position="outro")

    blend.append({
        "type": "narration",
        "text": outro_text
    })

    return blend


if __name__ == "__main__":
    blend = build_blend("reinventing yourself after failure")

    print("\n🔥 BLEND OUTPUT:\n")

    if not blend:
        print("No blend generated.")
    else:
        for step in blend:
            print(step)


