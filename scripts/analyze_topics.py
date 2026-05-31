import json
import glob
from collections import Counter


def extract_phrases(text):
    words = text.lower().split()

    phrases = []

    # 2-word and 3-word phrases
    for i in range(len(words) - 1):
        phrases.append(words[i] + " " + words[i + 1])

    for i in range(len(words) - 2):
        phrases.append(words[i] + " " + words[i + 1] + " " + words[i + 2])

    return phrases


def build_topic_patterns():
    files = glob.glob("segments/**/*.json", recursive=True)

    counter = Counter()

    for f in files[:1500]:  # sample size

        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)

            for seg in data:
                text = seg.get("text", "")

                phrases = extract_phrases(text)
                counter.update(phrases)

    # ✅ filter junk phrases
    patterns = [
        p for p, count in counter.most_common(200)
        if len(p.split()) >= 2 and count > 5
    ]

    with open("topic_patterns.json", "w") as f:
        json.dump(patterns[:100], f, indent=2)

    print("✅ Saved topic patterns")


if __name__ == "__main__":
    build_topic_patterns()
