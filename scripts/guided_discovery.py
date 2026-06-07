import faiss
import numpy as np
import json
import re
import boto3
import traceback

from openai import OpenAI
from sklearn.feature_extraction.text import CountVectorizer

# =========================================================
# ✅ CONFIG
# =========================================================

INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"

OUTPUT_FILE = "guided_topic_cards.json"

BUCKET = "podblendz-episode-audio"

MODEL = "text-embedding-3-small"

TOP_K = 120

# =========================================================
# ✅ SEED TOPICS
# =========================================================

SEED_TOPICS = [
    "artificial intelligence",
    "robotics",
    "machine learning",
    "startup funding",
    "venture capital",
    "future of work",
    "remote work",
    "creator economy",
    "productivity",
    "mental health",
    "nutrition",
    "longevity",
    "bitcoin",
    "cybersecurity",
    "relationships",
    "climate change",
    "space exploration",
    "education technology",
    "neuroscience",
    "business strategy",
    "software engineering",
    "AI agents",
    "automation",
    "economic systems",
    "geopolitics",
    "fitness",
    "biohacking",
    "podcasting",
    "social media",
    "marketing strategy"
]

# =========================================================
# ✅ STOPWORDS
# =========================================================

STOPWORDS = {
    "the", "and", "that", "with", "from",
    "have", "this", "about", "their",
    "would", "there", "could", "should",
    "what", "when", "where", "which",
    "while", "because", "being", "into",
    "through", "between", "those",
    "really", "actually", "basically",
    "something", "someone",
    "thing", "things", "people",
    "stuff", "make", "made",
    "getting", "going", "yeah",
    "okay", "dont", "cant",
    "thats", "theres", "youre",
    "just", "like", "know",
    "right", "good", "great",
    "able", "probably", "literally",
    "said", "saying", "think",
    "thinks", "talking", "talk",
    "want", "wanted", "maybe",
    "well", "very", "much"
}

# =========================================================
# ✅ WEAK WORDS
# =========================================================

WEAK_WORDS = {
    "like",
    "just",
    "really",
    "actually",
    "probably",
    "literally",
    "maybe",
    "think",
    "people",
    "going",
    "things",
    "stuff"
}

# =========================================================
# ✅ CLIENTS
# =========================================================

client = OpenAI()

s3 = boto3.client("s3")

# =========================================================
# ✅ LOAD FAISS
# =========================================================

print("📦 Loading FAISS index...")

index = faiss.read_index(INDEX_FILE)

print("✅ FAISS loaded")

with open(ID_MAP_FILE, "r") as f:
    id_map = json.load(f)

print(f"✅ Loaded {len(id_map)} IDs")

# =========================================================
# ✅ FETCH SEGMENT TEXT
# =========================================================

def fetch_segment_text(segment_id):

    try:

        parts = segment_id.split("_")

        file_key = "_".join(parts[:-1])

        idx = int(parts[-1])

        response = s3.get_object(
            Bucket=BUCKET,
            Key=file_key
        )

        data = json.loads(
            response["Body"].read()
        )

        segments = data.get("segments", [])

        if idx >= len(segments):
            return ""

        return segments[idx].get("text", "")

    except Exception:
        return ""

# =========================================================
# ✅ CLEAN TEXT
# =========================================================

def clean_text(text):

    text = text.lower()

    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)

    words = []

    for w in text.split():

        if len(w) <= 3:
            continue

        if w in STOPWORDS:
            continue

        words.append(w)

    return " ".join(words)

# =========================================================
# ✅ EMBED QUERY
# =========================================================

def embed_query(text):

    response = client.embeddings.create(
        model=MODEL,
        input=text
    )

    vector = np.array(
        [response.data[0].embedding],
        dtype=np.float32
    )

    # ✅ normalize for cosine similarity
    faiss.normalize_L2(vector)

    return vector

# =========================================================
# ✅ GENERATE TITLE
# =========================================================

def generate_title(topic, keywords):

    title_parts = []

    for word, score in keywords:

        if len(word) < 5:
            continue

        if word in STOPWORDS:
            continue

        title_parts.append(word)

        if len(title_parts) >= 4:
            break

    if title_parts:
        return " ".join(title_parts).title()

    return topic.title()

# =========================================================
# ✅ DEDUPLICATE PHRASES
# =========================================================

def deduplicate_phrases(ranked_phrases):

    cleaned = []

    seen = []

    for phrase, score in ranked_phrases:

        words = phrase.split()

        # ✅ Skip weak conversational phrases
        weak = False

        for w in words:
            if w in WEAK_WORDS:
                weak = True
                break

        if weak:
            continue

        signature = set(words)

        duplicate = False

        for existing in seen:

            overlap = signature.intersection(existing)

            if len(overlap) >= 4:
                duplicate = True
                break

        if duplicate:
            continue

        cleaned.append(phrase)

        seen.append(signature)

        if len(cleaned) >= 8:
            break

    return cleaned

# =========================================================
# ✅ MAIN DISCOVERY LOOP
# =========================================================

print("\n🧠 Starting guided semantic discovery...\n")

cards = []

for topic in SEED_TOPICS:

    print("=" * 60)
    print(f"🔍 Topic: {topic}")

    try:

        # -------------------------------------------------
        # ✅ EMBED TOPIC
        # -------------------------------------------------

        query_vector = embed_query(topic)

        # -------------------------------------------------
        # ✅ SEARCH FAISS
        # -------------------------------------------------

        distances, indices = index.search(
            query_vector,
            TOP_K
        )

        docs = []

        segment_ids = []

        # -------------------------------------------------
        # ✅ FETCH RESULTS
        # -------------------------------------------------

        for idx in indices[0]:

            if idx < 0:
                continue

            if idx >= len(id_map):
                continue

            segment_id = id_map[idx]

            text = fetch_segment_text(segment_id)

            if not text:
                continue

            cleaned = clean_text(text)

            if len(cleaned.split()) < 5:
                continue

            docs.append(cleaned)

            segment_ids.append(segment_id)

        print(f"✅ Retrieved docs: {len(docs)}")

        if len(docs) < 5:
            continue

        # =================================================
        # ✅ KEYWORD EXTRACTION
        # =================================================

        keyword_vectorizer = CountVectorizer(
            ngram_range=(1, 3),
            stop_words="english",
            max_features=150
        )

        X_keywords = keyword_vectorizer.fit_transform(docs)

        keyword_terms = (
            keyword_vectorizer.get_feature_names_out()
        )

        # ✅ Force dense matrix safely
        keyword_matrix = np.asarray(X_keywords)

        keyword_freqs = keyword_matrix.sum(axis=0)

        keyword_ranked = sorted(
            zip(keyword_terms, keyword_freqs),
            key=lambda x: x[1],
            reverse=True
        )

        # =================================================
        # ✅ PHRASE EXTRACTION
        # =================================================

        phrase_vectorizer = CountVectorizer(
            ngram_range=(4, 8),
            stop_words="english",
            max_features=150
        )

        X_phrases = phrase_vectorizer.fit_transform(docs)

        phrase_terms = (
            phrase_vectorizer.get_feature_names_out()
        )

        # ✅ Force dense matrix safely
        phrase_matrix = np.asarray(X_phrases)

        phrase_freqs = phrase_matrix.sum(axis=0)

        phrase_ranked = sorted(
            zip(phrase_terms, phrase_freqs),
            key=lambda x: x[1],
            reverse=True
        )

        # =================================================
        # ✅ CLEAN KEYWORDS
        # =================================================

        keywords = []

        seen_keywords = set()

        for word, score in keyword_ranked:

            if word in STOPWORDS:
                continue

            if len(word) < 5:
                continue

            if word in seen_keywords:
                continue

            skip = False

            for w in word.split():
                if w in WEAK_WORDS:
                    skip = True
                    break

            if skip:
                continue

            keywords.append((
                word,
                int(score)
            ))

            seen_keywords.add(word)

            if len(keywords) >= 15:
                break

        # =================================================
        # ✅ CLEAN PHRASES
        # =================================================

        phrases = deduplicate_phrases(
            phrase_ranked
        )

        # =================================================
        # ✅ BUILD CARD
        # =================================================

        title = generate_title(
            topic,
            keywords
        )

        card = {
            "topic": topic,
            "title": title,
            "keywords": keywords,
            "phrases": phrases,
            "related_segment_count": len(segment_ids),
            "sample_segments": segment_ids[:10]
        }

        cards.append(card)

        print(f"✅ Keywords extracted: {len(keywords)}")
        print(f"✅ Phrases extracted: {len(phrases)}")

    except Exception as e:

        print(f"⚠️ Failed topic: {topic}")
        print(e)

        traceback.print_exc()

# =========================================================
# ✅ SAVE OUTPUT
# =========================================================

print("\n💾 Saving guided discovery cards...")

with open(OUTPUT_FILE, "w") as f:

    json.dump(
        cards,
        f,
        indent=2
    )

# =========================================================
# ✅ SUMMARY
# =========================================================

print("\n✅ Guided semantic discovery complete!\n")

print(f"🎴 Topic cards generated: {len(cards)}")

print("\n🔥 TOP DISCOVERY CARDS:\n")

for card in cards[:10]:

    print("=" * 60)

    print(f"🎯 {card['title']}")

    print(f"📚 Seed Topic: {card['topic']}")

    print(
        f"📊 Related Segments: "
        f"{card['related_segment_count']}"
    )

    # ----------------------------------------------------
    # ✅ KEYWORDS
    # ----------------------------------------------------

    if card["keywords"]:

        print("\n🔑 Keywords:")

        for word, score in card["keywords"][:8]:

            print(f"   - {word} ({score})")

    # ----------------------------------------------------
    # ✅ PHRASES
    # ----------------------------------------------------

    if card["phrases"]:

        print("\n🧠 Semantic Phrases:")

        for phrase in card["phrases"][:4]:

            print(f"   - {phrase}")

print("\n🚀 DONE")