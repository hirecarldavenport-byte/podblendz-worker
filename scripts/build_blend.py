from search_test import search


def build_blend(query, max_segments=8):
    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query) or []

    if not results:
        print("❌ No results found.")
        return []

    selected_pool = []

    KEYWORDS = ["fail", "failure", "mistake", "growth", "change", "identity", "learn", "struggle"]

    # ✅ Step 1: LIGHT filtering only
    for r in results:
        text = r.get("text", "").strip().lower()

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

        # ✅ Instead of filtering OUT — we SCORE relevance
        relevance = 0
        for k in KEYWORDS:
            if k in text:
                relevance += 1

        selected_pool.append({
            **r,
            "relevance": relevance
        })

    if not selected_pool:
        print("❌ No usable segments.")
        return []

    # ✅ Step 2: rank smartly (score + thematic boost)
    selected_pool = sorted(
        selected_pool,
        key=lambda x: (x["relevance"], x["score"]),
        reverse=True
    )

    # ✅ Step 3: take top but allow diversity
    selected = selected_pool[:max_segments * 3]

    # ✅ Step 4: slice final set
    selected = selected[:max_segments]

    # ✅ Step 5: Build blend
    blend = []

    blend.append({
        "type": "narration",
        "text": f"This blend explores {query}. Let's connect a few ideas and see what emerges."
    })

    transitions = [
        "But that raises another question.",
        "And that idea shows up in a different way.",
        "But there's another layer to this.",
        "And this connects more deeply than it first seems.",
        "But from another angle, it looks different."
    ]

    for i, segment in enumerate(selected):
        blend.append({
            "type": "clip",
            "text": segment["text"],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "source": segment.get("source")
        })

        if i < len(selected) - 1:
            blend.append({
                "type": "narration",
                "text": transitions[i % len(transitions)]
            })

    blend.append({
        "type": "narration",
        "text": f"So maybe {query} isn’t about a single moment — it’s about how those moments build over time."
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


