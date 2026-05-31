from search_faiss import search
from collections import Counter
import json


SEED_QUERIES = [
    "science", "technology", "health", "mind",
    "learning", "risk", "money", "relationships",
    "future", "innovation", "biology", "space"
]


# =========================
# ✅ NORMALIZE TEXT
# =========================

def normalize(text):
    return (
        text.lower()
        .replace(",", "")
        .replace(".", "")
        .replace("?", "")
        .replace("!", "")
        .replace("'", "")
    )


# =========================
# ✅ EXTRACT 3-WORD PHRASES
# =========================

def extract_phrases(text):
    words = normalize(text).split()
    return [
        f"{words[i]} {words[i+1]} {words[i+2]}"
        for i in range(len(words) - 2)
    ]


# =========================
# ✅ HARD FILTER (FINAL)
# =========================

def clean_phrase(p):
    words = p.split()

    if len(words) != 3:
        return False

    # -------------------------
    # ❌ Remove weak words entirely
    # -------------------------
    blocked_words = {
        # grammar / connectors
        "the", "and", "of", "to", "in", "on", "for", "with",
        "about", "from", "into", "onto", "that", "this",

        # pronouns
        "you", "your", "they", "them", "their",
        "we", "i", "it", "its",

        # verbs / helpers / filler
        "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did",
        "will", "would", "can", "could", "should",
        "its", "im", "youre", "theyre"
    }

    if any(w in blocked_words for w in words):
        return False

    # -------------------------
    # ❌ Remove verb-like endings
    # -------------------------
    bad_suffixes = ("ing", "ed")

    for w in words:
        if w.endswith(bad_suffixes):
            return False

    # -------------------------
    # ✅ Must contain real topic anchors
    # -------------------------
    strong_keywords = {
        "science", "health", "brain", "decision", "risk",
        "money", "behavior", "genetic", "technology",
        "learning", "habit", "future", "energy",
        "space", "star", "biology", "innovation",
        "nuclear", "fusion", "evolution", "intelligence",
        "physics", "chemistry", "system",
        "process", "model", "structure"
    }

    if not any(w in strong_keywords for w in words):
        return False

    return True


# =========================
# ✅ MAIN BUILDER
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
        p for p, count in counter.most_common(150)
        if count >= 2
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
