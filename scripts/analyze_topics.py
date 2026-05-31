from search_faiss import search
from collections import Counter
import json


# =========================
# ✅ SEED QUERIES (coverage)
# =========================

SEED_QUERIES = [
    "science", "technology", "health", "mind",
    "learning", "risk", "money", "relationships",
    "future", "innovation", "biology", "space"
]


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


# =========================
# ✅ CLEAN + FILTER LOGIC
# =========================

def clean_phrase(p):
    # Minimum length
    if len(p) < 12:
        return False

    # Stop words (weak conversation edges)
    stop_words = {
        "the", "and", "that", "this", "with", "for", "you",
        "have", "from", "they", "your", "about", "when",
        "what", "which", "there", "been", "were", "going",
        "into", "onto", "just", "like", "really"
    }

    # Weak conversational patterns
    weak_phrases = {
        "it comes", "comes to", "going to", "be able",
        "in terms", "think about", "whether it",
        "a lot of", "kind of", "sort of",
        "you know", "we can", "i think"
    }

    words = p.split()

    # Reject weak edges
    if words[0] in stop_words or words[-1] in stop_words:
        return False

    # Reject obvious filler phrases
    for weak in weak_phrases:
        if weak in p:
            return False

    # Reject numeric noise
    if any(char.isdigit() for char in p):
        return False

    # ✅ Strong topic anchors (THIS is key)
    strong_words = {
        "science", "health", "brain", "decision", "risk",
        "money", "behavior", "genetic", "technology",
        "learning", "habit", "future", "energy",
        "space", "star", "biology", "innovation",
        "nuclear", "evolution", "intelligence"
    }

    if not any(sw in p for sw in strong_words):
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

            if not text or len(text) < 25:
                continue

            phrases = extract_phrases(text)

            for p in phrases:
                if clean_phrase(p):
                    counter[p] += 1

            total_segments += 1

    print(f"\n✅ Segments processed: {total_segments}")
    print(f"🔢 Unique phrases: {len(counter)}\n")

    # ✅ Select strongest patterns
    patterns = [
        p for p, count in counter.most_common(200)
        if count >= 2
    ]

    print(f"✅ Patterns selected: {len(patterns)}\n")

    # Save top patterns
    with open("topic_patterns.json", "w") as f:
        json.dump(patterns[:100], f, indent=2)

    print("✅ topic_patterns.json saved!\n")

    # Preview sample
    print("🔎 Sample patterns:")
    for p in patterns[:20]:
        print("-", p)


# =========================
# ✅ RUN
# =========================

if __name__ == "__main__":
    build_topic_patterns()

