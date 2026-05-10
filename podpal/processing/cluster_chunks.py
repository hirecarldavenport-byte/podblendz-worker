"""
Cluster Chunks

✅ Groups similar ideas across podcasts
✅ Filters low-quality chunks
✅ Produces meaningful multi-item clusters
✅ Ready for GPT labeling layer
"""

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


INPUT_DIR = Path("processed_chunks")
OUTPUT_FILE = Path("clusters.json")

# ✅ Load embedding model (light + fast)
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
                        "tag": chunk["tag"],
                    })

    return all_chunks


# =========================
# FILTER HIGH-SIGNAL CHUNKS
# =========================
def filter_chunks(chunks):
    return [
        c for c in chunks
        if c["tag"] in ("insight", "reflection", "example")
        and len(c["text"].split()) > 20
    ]


# =========================
# CLUSTERING
# =========================
def cluster_chunks(chunks, threshold=0.45):

    # ✅ Shorten text for better embeddings
    texts = [c["text"][:300] for c in chunks]

    # ✅ Convert to numpy (fixes sklearn error)
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

        # ✅ Only keep real clusters
        if len(cluster) >= 3:
            clusters.append(cluster)

    return clusters


# =========================
# SAVE CLUSTERS
# =========================
def save_clusters(clusters):

    output = []

    for cluster in clusters:

        output.append({
            "cluster_size": len(cluster),
            "sample_texts": [c["text"] for c in cluster[:3]],
            "sources": list({c["podcast"] for c in cluster}),
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

    print(f"[CLUSTER] Loaded {len(chunks)} raw chunks")

    chunks = filter_chunks(chunks)

    print(f"[CLUSTER] Filtered to {len(chunks)} high-signal chunks")

    clusters = cluster_chunks(chunks)

    print(f"[CLUSTER] Created {len(clusters)} clusters")

    save_clusters(clusters)


if __name__ == "__main__":
    run()