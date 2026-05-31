from search_faiss import search
from collections import Counter
import json


SEED_QUERIES = [
    "science", "technology", "health", "mind",
    "learning", "risk", "money", "relationships",
    "future", "innovation", "biology", "space"
]


def extract_phrases(text):
    words = text.lower().split()
    phrases = []

    for i in range(len(words) - 1):
        phrases.append(words[i] + " " + words[i + 1])

    for i in range(len(words) - 2):
        phrases.append(words[i] + " " + words[i + 1] + " " + words[i + 2])

    return phrases


def clean_phrase(p):
    if len(p) < 10:
        return False

    stop = {"the", "and", "that", "this", "with", "for", "you"}

    words = p.split()

    if words[0] in stop or words[-1] in stop:
        return False

    if any(char.isdigit() for char in p):
        return False

    return True


def build_topic_patterns():
    print("🔍 Building patterns from FAISS...\n")

    counter = Counter()
    total_segments = 0

    for q in SEED_QUERIES:
        print(f"➡️ Query: {q}")

        results = search(q, k=80)

        for r in results:
            text = r.get("text", "")

            if not text or len(text) < 25:
                continue

            phrases = extract_phrases(text)

            for p in phrases:
                if clean_phrase(p):
                    counter[p] += 1

            total_segments += 1

    print(f"\n✅ Segments processed: {total_segments}")
    print(f"🔢 Unique phrases: {len(counter)}")

    patterns = [
        p for p, c in counter.most_common(200)
        if c >= 2
    ]

    print(f"✅ Patterns selected: {len(patterns)}")

    with open("topic_patterns.json", "w") as f:
        json.dump(patterns[:100], f, indent=2)

    print("\n✅ topic_patterns.json created!\n")

    print("🔎 Sample patterns:")
    for p in patterns[:15]:
        print("-", p)


if __name__ == "__main__":
    build_topic_patterns()

