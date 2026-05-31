import json
import glob
from collections import Counter


def extract_phrases(text):
    words = text.lower().split()

    phrases = []

    # 2-word phrases
    for i in range(len(words) - 1):
        p = words[i] + " " + words[i + 1]
        phrases.append(p)

    # 3-word phrases
    for i in range(len(words) - 2):
        p = words[i] + " " + words[i + 1] + " " + words[i + 2]
        phrases.append(p)

    return phrases


def clean_phrase(p):
    bad_words = {"the", "and", "that", "this", "with", "for", "you"}

    words = p.split()

    # remove junk phrases like "and the", "you have"
    if words[0] in bad_words or words[-1] in bad_words:
        return False

    return True


def build_topic_patterns():
    files = glob.glob("segments/**/*.json", recursive=True)

    print(f"📂 Found {len(files)} files")

    counter = Counter()

    for f in files[:2000]:  # increased sample
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)

                for seg in data:
                    text = seg.get("text", "")
                    phrases = extract_phrases(text)

                    for p in phrases:
                        if clean_phrase(p):
                            counter[p] += 1
        except:
            continue

    print(f"🔢 Total phrase count: {len(counter)}")

    # ✅ RELAX FILTERS (KEY FIX)
    patterns = [
        p for p, count in counter.most_common(200)
        if count >= 2 and len(p) > 8
    ]

    print(f"✅ Patterns kept: {len(patterns)}")

    with open("topic_patterns.json", "w") as f:
        json.dump(patterns[:100], f, indent=2)

    print("✅ Saved topic_patterns.json")


if __name__ == "__main__":
    build_topic_patterns()
