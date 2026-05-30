from search_test import search
import random


def build_blend(query, max_segments=8):
    print(f"\n🎧 Building Blend: {query}\n")

    # ✅ Step 1: Get results (SAFE)
    results = search(query) or []

    # ✅ Safety check
    if not results or len(results) == 0:
        print("❌ No results found.")
        return []

    # ✅ Step 2: Limit + validate
    selected = []

    for r in results:
        if (
            not r.get("text")
            or len(r["text"].strip()) < 40
            or len(r["text"].split()) < 8
        ):
            continue

        selected.append(r)

        if len(selected) >= max_segments:
            break

    if len(selected) == 0:
        print("❌ No usable segments after filtering.")
        return []

    # ✅ Step 3: Shuffle slightly for variation
    random.shuffle(selected)

    # ✅ Step 4: Build blend structure
    blend = []

    # ✅ Better intro
    blend.append({
        "type": "narration",
        "text": f"This blend explores {query}. Let's look at different perspectives and how they connect."
    })

    # ✅ Main flow
    for i, segment in enumerate(selected):
        # ✅ Add clip
        blend.append({
            "type": "clip",
            "text": segment["text"],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "source": segment.get("source")
        })

        # ✅ Add smarter transition (variety helps later)
        if i < len(selected) - 1:
            blend.append({
                "type": "narration",
                "text": [
                    "But that idea leads somewhere deeper.",
                    "And that connects to another important perspective.",
                    "But there's another layer to this.",
                    "That same pattern shows up again in a different way."
                ][i % 4]
            })

    # ✅ Stronger ending
    blend.append({
        "type": "narration",
        "text": f"So the real takeaway is this: {query} is less about a single moment, and more about how you respond over time."
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
