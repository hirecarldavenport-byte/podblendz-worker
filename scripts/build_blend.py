from search_test import search


def build_blend(query, max_segments=8):
    print(f"\n🎧 Building Blend: {query}\n")

    # ✅ Step 1: Get results safely
    results = search(query) or []

    if not results:
        print("❌ No results found.")
        return []

    # ✅ Step 2: Thematic + quality filtering
    selected = []

    KEYWORDS = ["fail", "failure", "mistake", "growth", "change", "identity", "learn", "struggle"]

    for r in results:
        text = r.get("text", "").strip().lower()

        start = r.get("start")
        end = r.get("end")

        # ✅ compute duration safely
        duration = 0
        if start is not None and end is not None:
            duration = end - start

        if (
            not text
            or len(text) < 40
            or len(text.split()) < 7
            or duration < 6
            or text.endswith(("and", "but", "so", "or"))
        ):
            continue

        # ✅ Light thematic filter (NOT strict)
        if not any(k in text for k in KEYWORDS):
            continue

        selected.append(r)

        if len(selected) >= max_segments * 2:  # collect more, refine later
            break

    if not selected:
        print("❌ No usable segments after filtering.")
        return []

    # ✅ Step 3: Sort by score (NO shuffle)
    selected = sorted(selected, key=lambda x: x["score"], reverse=True)

    # ✅ Step 4: Final selection (top N)
    selected = selected[:max_segments]

    # ✅ Step 5: Build blend
    blend = []

    # ✅ Intro (neutral, flexible for narration upgrade later)
    blend.append({
        "type": "narration",
        "text": f"This blend explores {query}. Let's connect a few ideas and see what emerges."
    })

    # ✅ Transitions (light, non-repetitive)
    transitions = [
        "But that raises another question.",
        "And that idea shows up in a different way.",
        "But there's another layer to this.",
        "And this connects more deeply than it first seems.",
        "But that perspective isn't the whole story.",
        "And from another angle, it looks different."
    ]

    # ✅ Main flow
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

    # ✅ Ending (slightly stronger, but still generic)
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


