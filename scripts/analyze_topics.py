from search_faiss import search
from collections import Counter
import json


SEED_QUERIES = [
    "science", "technology", "health", "mind",
    "learning", "risk", "money", "relationships",
    "future", "innovation", "biology", "space"
]


# =========================
# ✅ TEXT NORMALIZATION
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
# ✅ EXTRACT PHRASES
# =========================

def extract_phrases(text):
    words = normalize(text).split()

    return [
        f"{words[i]} {words[i+1]} {words[i+2]}"
        for i in range(len(words) - 2)
    ]


# =========================
# ✅ HARD BLOCK (CRITICAL FIX)
# =========================

BLOCK_PHRASES = {
    "when it comes",
    "it comes to",
    "a lot of",
    "in terms of",
    "going to be",
    "able to be",
    "be able to",
    "you know its",
    "you know its",
    "kind of thing",
    "sort of thing",
    "a little bit",
    "do you think",
    "and so on"
}


BLOCK_WORDS = {
    "the", "and", "of", "to", "in", "on",
    "for", "with", "about", "from",
    "that", "this", "you", "your",
    "they", "them", "we", "it",
    "is", "are", "was", "were",
    "but", "so", "then", "just",
    "like", "okay", "well"
}


# =========================
# ✅ SCORING FUNCTION
# =========================

def score_phrase(p, freq):
    if p in BLOCK_PHRASES:
        return -999  # 🔥 kill immediately

    words = p.split()
    score = 0

    # ✅ Frequency still matters
    score += freq * 2

    # ✅ Reward strong topic words
    strong = {
        "science", "health", "brain", "decision", "risk",
        "money", "behavior", "genetic", "technology",
        "learning", "habit", "future", "energy",
        "space", "biology", "innovation",
        "nuclear", "fusion", "physics",
        "system", "process", "model"
    }

    score += sum(3 for w in words if w in strong)

    # ❌ Penalize filler words HARD
    score -= sum(4 for w in words if w in BLOCK_WORDS)

    # ❌ Penalize weak endings
    if any(w.endswith(("ing", "ed")) for w in words):
        score -= 2

    return score


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
                counter[p] += 1

            total_segments += 1

    print(f"\n✅ Segments processed: {total_segments}")
    print(f"🔢 Unique phrases: {len(counter)}\n")

    # ✅ Score + filter
    scored = [
        (p, score_phrase(p, freq))
        for p, freq in counter.items()
        if freq >= 2
    ]

    scored.sort(key=lambda x: x[1], reverse=True)

    # ✅ Remove any remaining negative junk
    patterns = [p for p, s in scored if s > 0][:100]

    print(f"✅ Patterns selected: {len(patterns)}\n")

    with open("topic_patterns.json", "w") as f:
        json.dump(patterns, f, indent=2)

    print("✅ topic_patterns.json saved!\n")

    print("🔎 Sample patterns:")
    for p in patterns[:20]:
        print("-", p)


if __name__ == "__main__":
    build_topic_patterns()

