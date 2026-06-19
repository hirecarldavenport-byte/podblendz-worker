import faiss
import numpy as np
import json
import re
import boto3
import traceback

from openai import OpenAI
from sklearn.feature_extraction.text import CountVectorizer
from pathlib import Path

# =========================================================
# ✅ CONFIG
# =========================================================

INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"

OUTPUT_FILE = "guided_topic_cards.json"

METADATA_ROOT = Path("ingestion/episode_metadata")

BUCKET = "podblendz-episode-audio"

MODEL = "text-embedding-3-small"

TOP_K = 120

# =========================================================
# ✅ SEED TOPICS
# =========================================================

SEED_TOPICS = [
    "future of artificial intelligence",
    "AI agents and automation",
    "humanoid robotics systems",
    "machine learning platforms",
    "startup funding ecosystems",
    "venture capital investing",
    "future of remote work",
    "creator economy monetization",
    "productivity systems",
    "mental health and wellness",
    "nutrition and metabolism",
    "longevity research",
    "bitcoin and crypto markets",
    "cybersecurity threats",
    "modern relationships",
    "climate change innovation",
    "space exploration technology",
    "education technology platforms",
    "brain science and neuroscience",
    "business growth strategy",
    "software engineering systems",
    "AI replacing labor",
    "economic systems and markets",
    "global geopolitics",
    "fitness and performance",
    "biohacking optimization",
    "podcasting and media",
    "social media influence",
    "marketing and brand strategy"
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
    "well", "very", "much",
    "years", "later", "today",
    "interesting", "important",
    "thing", "time"
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
    "stuff",
    "years",
    "later",
    "today",
    "interesting",
    "important",
    "thing",
    "time"
}

# =========================================================
# ✅ CLIENTS
# =========================================================

client = OpenAI()

s3 = boto3.client("s3")

# =========================================================
# ✅ LOAD FAISS INDEX
# =========================================================

print("📦 Loading FAISS index...")

index = faiss.read_index(INDEX_FILE)

print("✅ FAISS loaded")

with open(ID_MAP_FILE, "r") as f:
    id_map = json.load(f)

print(f"✅ Loaded {len(id_map)} IDs")


# =========================================================
# ✅ LOAD EPISODE METADATA
# =========================================================
episode_metadata = {}

print("📚 Loading episode metadata...")
for metadata_file in METADATA_ROOT.rglob("*.json"):
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            episode_id = data.get("episode_id")
            if episode_id:
                episode_metadata[episode_id] = data
    except Exception:
                   continue
    print(
        f"✅ Loaded {len(episode_metadata)} "
        f"metadata records"
    )
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
# ✅ EXTRACT EPISODE ID
# =========================================================
def extract_episode_id(segment_id):
    
    try:
        filename = segment_id.split("/")[-1]
        episode_id = filename.split(".json")[0]
        return episode_id
    except Exception:
        return None
# =========================================================
# ✅ CLEAN TEXT
# =========================================================

def clean_text(text):

    text = text.lower()

    text = re.sub(
        r"[^a-zA-Z0-9\s]",
        " ",
        text
    )

    cleaned = []

    for word in text.split():

        if len(word) <= 3:
            continue

        if word in STOPWORDS:
            continue

        cleaned.append(word)

    return " ".join(cleaned)

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

    faiss.normalize_L2(vector)

    return vector

# =========================================================
# ✅ GENERATE TITLE
# =========================================================

def generate_title(topic, keywords):

    # Use topic directly if it's already clean
    if topic and len(topic.strip()) > 0:

        return topic.title()

    # Fallback cleanup logic
    seen = set()

    cleaned = []

    for keyword in keywords:

        # Keywords might be tuples
        if isinstance(keyword, tuple):
            keyword = keyword[0]

        normalized = keyword.lower()

        if normalized not in seen:

            seen.add(normalized)

            cleaned.append(keyword)

    return " ".join(cleaned[:4]).title()

# =========================================================
# ✅ CLEAN PHRASES
# =========================================================

def deduplicate_phrases(phrases, topic):

    cleaned = []

    seen = []

    topic_words = set(
        clean_text(topic).split()
    )

    for phrase, score in phrases:

        words = phrase.split()

        if len(words) < 3:
            continue

        # ✅ reject phrases with weak words
        skip = False

        for word in words:

            if word in WEAK_WORDS:
                skip = True
                break

        if skip:
            continue

        # ✅ reject phrases containing years/numbers
        if any(char.isdigit() for char in phrase):
            continue

        signature = set(words)

        duplicate = False

        for existing in seen:

            overlap = signature.intersection(existing)

            if len(overlap) >= 3:
                duplicate = True
                break

        if duplicate:
            continue

        relevance = len(
            signature.intersection(topic_words)
        )

        cleaned.append((
            phrase,
            relevance
        ))

        seen.append(signature)

    cleaned.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return [x[0] for x in cleaned[:8]]

# =========================================================
# ✅ MAIN DISCOVERY LOOP
# =========================================================

print("\n🧠 Starting guided semantic discovery...\n")

cards = []

for topic in SEED_TOPICS:

    print("=" * 60)
    print(f"🔍 Topic: {topic}")

    try:

        query_vector = embed_query(topic)

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

        keyword_matrix = X_keywords.toarray()

        keyword_freqs = np.sum(
            keyword_matrix,
            axis=0
        ).astype(float)

        keyword_ranked = sorted(
            zip(keyword_terms, keyword_freqs),
            key=lambda x: float(x[1]),
            reverse=True
        )

        # =================================================
        # ✅ PHRASE EXTRACTION
        # =================================================

        phrase_vectorizer = CountVectorizer(
            ngram_range=(3, 5),
            stop_words="english",
            max_features=150
        )

        X_phrases = phrase_vectorizer.fit_transform(docs)

        phrase_terms = (
            phrase_vectorizer.get_feature_names_out()
        )

        phrase_matrix = X_phrases.toarray()

        phrase_freqs = np.sum(
            phrase_matrix,
            axis=0
        ).astype(float)

        phrase_ranked = sorted(
            zip(phrase_terms, phrase_freqs),
            key=lambda x: float(x[1]),
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

            if any(w in WEAK_WORDS for w in word.split()):
                continue

            if any(char.isdigit() for char in word):
                continue

            keywords.append((
                word,
                round(float(score), 2)
            ))

            seen_keywords.add(word)

            if len(keywords) >= 15:
                break

        print(f"✅ Keywords extracted: {len(keywords)}")

        # =================================================
        # ✅ CLEAN PHRASES
        # =================================================

        cleaned_phrases = deduplicate_phrases(
            phrase_ranked,
            topic
        )

        print(
            f"✅ Phrases extracted: "
            f"{len(cleaned_phrases)}"
        )
        # =================================================
        # ✅ SOURCE EPISODES
        # =================================================

        source_episodes = []
        seen_episodes = set()
        for segment_id in segment_ids:
            episode_id = extract_episode_id(
                segment_id
            )
            if not episode_id:
                continue
            if episode_id in seen_episodes:
                continue
            metadata = episode_metadata.get(
                episode_id
            )
            if not metadata:
                continue
            source_episodes.append({
                "episode_id": episode_id,
                "episode_title":
                 metadata.get("title"),
                 "published":
                 metadata.get("published"),
                 "podcast_title":
                 metadata.get(
                     "podcast",
                     {}
                      ).get("title")
                      })
            seen_episodes.add(
                 episode_id
            )
            if len(source_episodes) >= 5:
                break

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
            "phrases": cleaned_phrases,
            "related_segment_count": len(segment_ids),
            "source_episodes":
            
source_episodes,

            "sample_segments": segment_ids[:10]
        }

        cards.append(card)

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