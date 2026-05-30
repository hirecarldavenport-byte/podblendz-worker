from search_test import search
from openai import OpenAI
import os

# ✅ OpenAI client
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ ✅ Narration Generator (FLOW-OPTIMIZED)
def generate_narration(prev_text, next_text, query, position="middle"):
    if position == "intro":
        prompt = f"""
Create a short intro for a guided audio experience.

Topic: {query}

This blends multiple perspectives.

Keep it engaging, NOT conclusive.
Max 30 words.
"""

    elif position == "outro":
        prompt = f"""
Create a short closing reflection.

Topic: {query}

Do NOT summarize everything.
Leave the listener thinking.

Max 30 words.
"""

    else:
        prompt = f"""
You are guiding a listener through different perspectives.

Topic: {query}

Previous idea:
"{prev_text}"

Next idea:
"{next_text}"

Rules:
- DO NOT summarize the topic
- DO NOT conclude
- Highlight contrast or curiosity
- Keep flow moving forward

Max 20 words.
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

    KEYWORDS = ["fail", "failure", "mistake", "growth", "change", "identity", "learn", "struggle"]

    selected_pool = []

    # ✅ Step 1 — Filtering + scoring
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

    # ✅ Step 2 — Rank by relevance + score
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], x["score"]),
        reverse=True
    )

    # ✅ Step 3 — Expand pool (prevents collapse)
    candidates = selected_pool[:max_segments * 5]

    # ✅ ✅ Step 4 — SOFT diversity (FIXED)
    selected = []
    source_counts = {}

    for r in candidates:
        source = r.get("source") or ""
        parts = source.split("/")
        source_key = parts[2] if len(parts) > 2 else source

        count = source_counts.get(source_key, 0)

        # ✅ Prefer diversity first
        if count < 2:
            selected.append(r)
            source_counts[source_key] = count + 1

        # ✅ Then allow overflow to fill required segments
        elif len(selected) < max_segments:
            selected.append(r)

        if len(selected) >= max_segments:
            break

    if not selected:
        print("❌ No segments selected.")
        return []

    if len(selected) < max_segments:
        print(f"⚠️ Only {len(selected)} segments found — consider loosening filters")

    # ✅ Step 5 — Build Blend
    blend = []

    # ✅ Intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

    # ✅ Flow (clip → short narration → clip)
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

            transition = generate_narration(
                prev_text=segment["text"],
                next_text=next_seg["text"],
                query=query
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


# ✅ ✅ RUN TEST
if __name__ == "__main__":
    blend = build_blend("reinventing yourself after failure")

    print("\n🔥 BLEND OUTPUT:\n")

    if not blend:
        print("No blend generated.")
    else:
        for step in blend:
            print(step)



