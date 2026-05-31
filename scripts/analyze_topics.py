from search_faiss import search
from collections import Counter
import json


SEED_QUERIES = [
    "science", "technology", "health", "mind",
    "learning", "risk", "money", "relationships",
    "future", "innovation", "biology", "space"
]


# =========================
# ✅ BASIC CLEANING
# =========================

def normalize(text):
    return (
        text.lower()
        .replace(",", "")
        .replace(".", "")
        .replace("?", "")
        .replace("!", "")
    )


# =========================
# ✅ PHRASE EXTRACTION
# =========================

def extract_phrases(text):
    words = normalize(text).split()
    phrases = []

    # 3-word phrases ONLY (key improvement)
    for i in range(len(words) - 2):
        phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")

    return phrases


# =========================
# ✅ STRUCTURAL FILTER
# =========================

def clean_phrase(p):
    words = p.split()

    if len(words) != 3:
        return False

    # -------------------------
    # ❌ Skip grammar words
    # -------------------------
    stopwords = {
        "the", "and", "of", "to", "in", "on", "for", "with",
        "about", "from", "into", "onto", "that", "this",
        "you", "your", "they", "them", "is", "are", "was",
        "were", "be", "been", "it", "we", "i"
    }

    # reject if ANY word is weak
    if any(w in stopwords for w in words):
        return False

    # -------------------------
    # ✅ Must contain content words
    # -------------------------
    strong_keywords = {
        "science", "health", "brain", "decision",
        "risk", "money", "behavior", "genetic",
        "technology", "learning", "habit", "future",
        "energy", "space", "star", "biology",
        "innovation", "nuclear", "fusion",
        "evolution", "intelligence", "physics",
        "system", "process", "development",
        "model"
    }

    if not any(w in strong_keywords for w in words):
        return False

    return True


# =========================
# ✅ MAIN
# =========================

def build_topic_patterns():
    print("🔍 Building patterns from FAISS...\n")

    counter = Counter()
    total_segments = 0

    for q in SEED_QUERIES:
        print(f"➡️ Query: {q}")

        results = search(q, k=80)

        for r in results:
            text = r.get("text", "")

            if not text or len(text) < 30:
                continue

            phrases = extract_phrases(text)

            for p in phrases:
                if clean_phrase(p):
                    counter[p] += 1

            total_segments += 1

    print(f"\n✅ Segments processed: {total_segments}")
    print(f"🔢 Unique phrases: {len(counter)}\n")

    patterns = [
        p for p, c in counter.most_common(150)
        if c >= 2
    ]

    print(f"✅ Patterns selected: {len(patterns)}\n")

    with open("topic_patterns.json", "w") as f:
        json.dump(patterns[:100], f, indent=2)

    print("✅ topic_patterns.json saved!\n")

    print("🔎 Sample patterns:")
    for p in patterns[:20]:
        print("-", p)


if __name__ == "__main__":
    build_topic_patterns()
