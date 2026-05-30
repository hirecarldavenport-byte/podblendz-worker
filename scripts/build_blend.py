from search_test import search
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ✅ ✅ HIGH-LEVEL ANALYTICAL NARRATION
def generate_narration(prev_text, next_text, query, position="middle"):

    if position == "intro":
        prompt = f"""
You are an expert in educational research and analytical writing.

Introduce a guided intellectual exploration.

Topic: {query}

Frame this as an investigation of multiple perspectives.
Avoid clichés. Avoid motivational tone.

Be precise, reflective, and grounded.

Max 35 words.
"""

    elif position == "outro":
        prompt = f"""
Provide a closing reflection as a research-oriented thinker.

Topic: {query}

Do NOT summarize everything.
Instead, surface a deeper insight or open-ended reflection.

Max 35 words.
"""

    else:
        prompt = f"""
You are synthesizing insights across perspectives as a scholarly thinker.

Topic: {query}

Previous idea:
"{prev_text}"

Next idea:
"{next_text}"

Instructions:
- Identify contrast, tension, or shift in perspective
- Avoid generic phrasing like "this shows" or "this highlights"
- Avoid summarizing the topic
- Maintain intellectual tone (like an essay or lecture)
- Keep it concise and precise

Max 25 words.
Avoid repetition of phrasing used earlier.
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

    # ✅ Step 1 — Filtering + relevance scoring
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

    # ✅ Step 2 — Deduplicate by text (IMPORTANT FIX)
    seen_texts = set()
    unique_pool = []

    for r in selected_pool:
        t = r.get("text")
        if t not in seen_texts:
            seen_texts.add(t)
            unique_pool.append(r)

    selected_pool = unique_pool

    # ✅ Step 3 — Sort by relevance + semantic score
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], x["score"]),
        reverse=True
    )

    # ✅ Step 4 — Expand pool size
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

    # ✅ Step 6 — Build Blend
    blend = []

    # ✅ Intro
    blend.append({
        "type": "narration",
        "text": generate_narration("", "", query, position="intro")
    })

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


# ✅ ✅ TEST RUN
if __name__ == "__main__":
    blend = build_blend("reinventing yourself after failure")

    print("\n🔥 BLEND OUTPUT:\n")

    if not blend:
        print("No blend generated.")
    else:
        for step in blend:
            print(step)




