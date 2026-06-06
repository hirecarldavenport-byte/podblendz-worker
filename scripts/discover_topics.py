import faiss
import numpy as np
import json
import random
import re
import traceback
import boto3

from collections import defaultdict
from typing import cast

import umap
import hdbscan

from sklearn.feature_extraction.text import CountVectorizer

# =========================================================
# ✅ CONFIG
# =========================================================

INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"

OUTPUT_CLUSTERS = "topic_clusters.json"
OUTPUT_MAP = "semantic_map.json"
OUTPUT_CARDS = "discovery_cards.json"

BUCKET = "podblendz-episode-audio"

# ✅ IMPORTANT
# Start smaller first for testing/stability
SAMPLE_SIZE = 3000

# ✅ HDBSCAN SETTINGS
MIN_CLUSTER_SIZE = 25
MIN_SAMPLES = 10

# =========================================================
# ✅ AWS CLIENT
# =========================================================

s3 = boto3.client("s3")

# =========================================================
# ✅ STOPWORDS
# Spoken-language cleanup
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
    "theyre", "wasnt", "wouldnt",
    "couldnt", "youve", "weve",
    "hes", "shes", "lets",
    "kind", "sort", "maybe"
}

# =========================================================
# ✅ LOAD FAISS INDEX
# =========================================================

print("📦 Loading FAISS index...")

index = faiss.read_index(INDEX_FILE)

print("✅ FAISS loaded")

# =========================================================
# ✅ LOAD ID MAP
# =========================================================

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
# ✅ EXTRACT SAMPLE VECTORS
# =========================================================

print("\n🧠 Sampling semantic vectors...")

total_vectors = index.ntotal

sample_size = min(SAMPLE_SIZE, total_vectors)

sample_indices = random.sample(
    range(total_vectors),
    sample_size
)

vectors = []
sampled_ids = []

for idx in sample_indices:

    vector = index.reconstruct(idx)

    vectors.append(vector)

    sampled_ids.append(id_map[idx])

vectors = np.array(vectors).astype("float32")

print(f"✅ Sampled vectors: {len(vectors)}")

# =========================================================
# ✅ BUILD SEMANTIC MAP (UMAP)
# =========================================================

print("\n🌌 Building semantic neighborhood map...")

reducer = umap.UMAP(
    n_neighbors=15,
    min_dist=0.1,
    metric="cosine",
    random_state=42
)

embedding_2d = np.array(
    reducer.fit_transform(vectors),
    dtype=np.float32
)

print("✅ UMAP complete")

# =========================================================
# ✅ SEMANTIC CLUSTERING
# =========================================================

print("\n🔍 Discovering semantic neighborhoods...")

clusterer = hdbscan.HDBSCAN(
    min_cluster_size=MIN_CLUSTER_SIZE,
    min_samples=MIN_SAMPLES,
    metric="euclidean"
)

try:

    labels = clusterer.fit_predict(embedding_2d)

except Exception as e:

    print("❌ HDBSCAN clustering failed")
    print(e)

    traceback.print_exc()

    raise

print("✅ Clustering complete")

# =========================================================
# ✅ NOISE ANALYSIS
# =========================================================

noise_count = np.sum(labels == -1)

print(f"🧹 Noise points removed: {noise_count}")

# =========================================================
# ✅ BUILD CLUSTERS
# =========================================================

clusters = defaultdict(list)

for i, label in enumerate(labels):

    # ✅ Ignore noise points
    if label == -1:
        continue

    coords = embedding_2d[i]

    clusters[int(label)].append({
        "segment_id": sampled_ids[i],
        "x": float(coords[0]),
        "y": float(coords[1]),
    })

print(f"✅ Semantic neighborhoods found: {len(clusters)}")

largest_cluster = max(
    [len(v) for v in clusters.values()],
    default=0
)

print(f"🔥 Largest cluster size: {largest_cluster}")

# =========================================================
# ✅ CLEAN TEXT
# =========================================================

def clean_text(text):

    text = text.lower()

    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)

    words = [
        w for w in text.split()
        if len(w) > 3 and w not in STOPWORDS
    ]

    return " ".join(words)

# =========================================================
# ✅ TOPIC LABEL GENERATION
# =========================================================

print("\n🧬 Generating semantic labels...")

cluster_labels = {}

for cluster_id, items in clusters.items():

    docs = []

    print(f"🔎 Processing cluster {cluster_id}...")

    # ✅ Pull REAL transcript text
    for item in items[:500]:

        seg_id = item["segment_id"]

        raw_text = fetch_segment_text(seg_id)

        if not raw_text:
            continue

        cleaned = clean_text(raw_text)

        if len(cleaned.split()) >= 5:
            docs.append(cleaned)

    print(f"   ✅ Transcript docs collected: {len(docs)}")

    if len(docs) < 5:

        cluster_labels[cluster_id] = {
            "topic_terms": [],
            "cluster_size": len(items)
        }

        continue

    vectorizer = CountVectorizer(
        ngram_range=(5, 8),
        stop_words="english",
        max_features=50
    )

    try:

        X = vectorizer.fit_transform(docs)

        X = cast(np.ndarray, X)

        terms = vectorizer.get_feature_names_out()

        freqs = np.asarray(
            X.sum(axis=0)
        ).ravel()

        ranked = sorted(
            zip(terms, freqs),
            key=lambda x: x[1],
            reverse=True
        )

        top_terms = []

        # ✅ Reduce duplicate-like phrases
        seen = set()

        for term, score in ranked:

            simplified = frozenset(term.split())

            duplicate = False

            for existing in seen:

                overlap = simplified.intersection(existing)

                if len(overlap) >= 4:
                    duplicate = True
                    break

            if duplicate:
                continue

            top_terms.append(term)

            seen.add(simplified)

            if len(top_terms) >= 5:
                break

    except Exception as e:

        print(f"⚠️ Failed labeling cluster {cluster_id}")
        print(e)

        top_terms = []

    cluster_labels[cluster_id] = {
        "topic_terms": top_terms,
        "cluster_size": len(items)
    }

print("✅ Topic labeling complete")

# =========================================================
# ✅ BUILD DISCOVERY CARDS
# =========================================================

print("\n🎴 Building discovery cards...")

cards = []

for cluster_id, info in cluster_labels.items():

    cluster_size = info["cluster_size"]

    if cluster_size < 15:
        continue

    top_terms = info["topic_terms"]

    title = " / ".join(top_terms[:2])

    if not title.strip():
        title = f"semantic_cluster_{cluster_id}"

    card = {
        "cluster_id": cluster_id,
        "title": title,
        "size": cluster_size,
        "top_terms": top_terms,
        "sample_segments": [
            x["segment_id"]
            for x in clusters[cluster_id][:10]
        ]
    }

    cards.append(card)

# ✅ Largest semantic groups first
cards.sort(
    key=lambda x: x["size"],
    reverse=True
)

print(f"✅ Discovery cards created: {len(cards)}")

# =========================================================
# ✅ SAVE CLUSTERS
# =========================================================

print("\n💾 Saving outputs...")

with open(OUTPUT_CLUSTERS, "w") as f:

    json.dump(
        {
            str(k): v
            for k, v in clusters.items()
        },
        f,
        indent=2
    )

# =========================================================
# ✅ SAVE SEMANTIC MAP
# =========================================================

semantic_map = []

for i in range(len(sampled_ids)):

    semantic_map.append({
        "segment_id": sampled_ids[i],
        "x": float(embedding_2d[i, 0]),
        "y": float(embedding_2d[i, 1]),
        "cluster": int(labels[i])
    })

with open(OUTPUT_MAP, "w") as f:

    json.dump(
        semantic_map,
        f,
        indent=2
    )

# =========================================================
# ✅ SAVE DISCOVERY CARDS
# =========================================================

with open(OUTPUT_CARDS, "w") as f:

    json.dump(
        cards,
        f,
        indent=2
    )

# =========================================================
# ✅ SUMMARY
# =========================================================

print("\n✅ Semantic discovery pipeline complete!\n")

print(f"🧠 Vectors analyzed: {len(vectors)}")
print(f"🌌 Semantic neighborhoods: {len(clusters)}")
print(f"🎴 Discovery cards: {len(cards)}")

print("\n🔥 TOP DISCOVERY CARDS:\n")

for card in cards[:15]:

    print("=" * 60)

    print(f"🎯 {card['title']}")

    print(f"📊 Cluster Size: {card['size']}")

    if card["top_terms"]:

        print("🧠 Topics:")

        for term in card["top_terms"][:5]:

            print(f"   - {term}")

print("\n🚀 DONE")