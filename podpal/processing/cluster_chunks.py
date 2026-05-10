"""
Chunk Clustering Module

✅ Groups✅ Uses embedding similarity✅ Groups similar ideas across podcasts
✅ Outputs clusters of related insights
"""

import json
from pathlib import Path
from collections import defaultdict

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


INPUT_DIR = Path("processed_chunks")
OUTPUT_FILE = Path("clusters.json")


# ✅ Load embedding model (fast + free)
model = SentenceTransformer("all-MiniLM-L6-v2")


# =========================
# LOAD CHUNKS
# =========================

def load_all_chunks():
    all_chunks = []

    for podcast_dir in INPUT_DIR.iterdir():
        if not podcast_dir.is_dir():
            continue

        for file in podcast_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

                for chunk in data.get("chunks", []):
                    all_chunks.append({
                        "podcast": data["podcast_id"],
                        "episode": data["episode_id"],
                        "text": chunk["text"],
                        "tag": chunk["tag"]
                    })

    return all_chunks


# =========================
# CLUSTERING LOGIC
# =========================

def cluster_chunks(chunks, threshold=0.55):

    texts = [c["text"] for c in chunks]

    embeddings = model.encode(texts, convert_to_numpy=True)
    similarity_matrix = cosine_similarity(embeddings)

    visited = set()
    clusters = []

    for i in range(len(chunks)):

        if i in visited:
            continue

        cluster = [chunks[i]]
        visited.add(i)

        for j in range(i + 1, len(chunks)):
            if j in visited:
                continue

            if similarity_matrix[i][j] > threshold:
                cluster.append(chunks[j])
                visited.add(j)

        clusters.append(cluster)

    return clusters


# =========================
# SAVE OUTPUT
# =========================

def save_clusters(clusters):

    output = []

    for cluster in clusters:

        output.append({
            "size": len(cluster),
            "examples": [c["text"] for c in cluster[:3]]
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"[CLUSTER] Saved to {OUTPUT_FILE}")


# =========================
# MAIN
# =========================

def run():

    print("[CLUSTER] Loading chunks...")
    chunks = load_all_chunks()

    print(f"[CLUSTER] Loaded {len(chunks)} chunks")

    clusters = cluster_chunks(chunks)

    print(f"[CLUSTER] Created {len(clusters)} clusters")

    save_clusters(clusters)


if __name__ == "__main__":
    run()
