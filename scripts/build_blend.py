from search_test import search
import random


def build_blend(query, max_segments=8):
    print(f"\n🎧 Building Blend: {query}\n")

    # ✅ Step 1: Get results safely
    results = search(query) or []

    if not results:
        print("❌ No results found.")
        return []

    # ✅ Step 2: Select good segments (balanced filtering)
    selected = []

    for r in results:
        text = r.get("text", "").strip()

        start = r.get("start")
        end = r.get("end")

        # ✅ compute duration safely
        duration = 0
        if start is not None and end is not None:
            duration = end - start

        # ✅ balanced filtering (FAST + practical)
        if (
            not text
            or len(text) < 40                 # reasonable minimum
            or len(text.split()) < 7          # avoids fragments
            or duration < 6                  # 🔥 very important (avoid tiny clips)
            or text.lower().endswith(("and", "but", "so", "or"))
        ):
            continue

        selected.append(r)

        if len(selected) >= max_segments:
            break

    if not selected:
        print("❌ No usable segments after filtering.")
        return []

    # ✅ Step 3: Slight shuffle (keeps top signals but adds variety)
    random.shuffle(selected)

    # ✅ Step 4: Build blend
    blend = []

    # ✅ Intro
    blend.append({
        "type": "narration",
        "text": f"This blend explores {query}. Let's connect a few ideas and see what emerges."
    })

    # ✅ Main flow
    for i, segment in enumerate(selected):

        # ✅ clip
        blend.append({
            "type": "clip",
            "text": segment["text"],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "source": segment.get("source")
        })

        # ✅ transitions (only between clips)
        if i < len(selected) - 1:
            transitions = [
                "But that raises another question.",
                "And that idea shows up again in a different way.",
                "But there's another angle to this.",
                "And this connects more deeply than it first seems."
            ]

            blend.append({
                "type": "narration",
                "text": transitions[i % len(transitions)]
            })

    # ✅ Ending
    blend.append({
        "type": "narration",
        "text": f"So maybe {query} isn’t about a single moment — it’s about how those moments compound over time."
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

