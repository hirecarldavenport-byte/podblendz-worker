import os
import glob
import json
from collections import Counter


# =========================
# ✅ RESOLVE PROJECT PATH
# =========================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGMENTS_PATH = os.path.join(BASE_DIR, "segments", "**", "*.json")


# =========================
# ✅ PHRASE EXTRACTION
# =========================

def extract_phrases(text):
    words = text.lower().split()

    phrases = []

    # 2-word phrases
    for i in range(len(words) - 1):
        phrases.append(f"{words[i]} {words[i + 1]}")

    # 3-word phrases
    for i in range(len(words) - 2):
        phrases.append(f"{words[i]} {words[i + 1]} {words[i + 2]}")

    return phrases


def clean_phrase(phrase):
    stop_words = {
        "the", "and", "that", "this", "with", "for", "you",
        "have", "from", "they", "your", "about"
    }

    words = phrase.split()

    # remove junk edges
    if words[0] in stop_words or words[-1] in stop_words:
        return False

    # remove short garbage phrases
    if len(phrase) < 8:
        return False

    # avoid numeric/random artifacts
    if any(char.isdigit() for char in phrase):
        return False

    return True


# =========================
# ✅ MAIN ANALYSIS
# =========================

def build_topic_patterns():

    print("🔍 Searching for segment files...\n")

    files = glob.glob(SEGMENTS_PATH, recursive=True)

    print(f"📂 Found {len(files)} files\n")

    if len(files) == 0:
        print("❌ No files found — check your segments path.")
        return

    counter = Counter()

    processed_files = 0
    processed_segments = 0

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)

                for seg in data:
                    text = seg.get("text", "")
                    if not text or len(text) < 20:
                        continue

                    phrases = extract_phrases(text)

                    for p in phrases:
                        if clean_phrase(p):
                            counter[p] += 1

                    processed_segments += 1

            processed_files += 1

        except Exception:
            continue

    print(f"✅ Processed files: {processed_files}")
    print(f"✅ Processed segments: {processed_segments}")
    print(f"🔢 Unique phrases: {len(counter)}\n")

    # ✅ RELAXED FILTER (important)
    patterns = [
        p for p, count in counter.most_common(300)
        if count >= 3
    ]

    print(f"✅ Patterns selected: {len(patterns)}\n")

    OUTPUT_PATH = os.path.join(BASE_DIR, "topic_patterns.json")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(patterns[:100], f, indent=2)

    print("✅ Saved topic_patterns.json")
    print(f"📁 Location: {OUTPUT_PATH}\n")

    # ✅ show preview
    print("🔎 Sample patterns:")
    for p in patterns[:20]:
        print(f"- {p}")


# =========================
# ✅ RUN
# =========================

if __name__ == "__main__":
    build_topic_patterns()

