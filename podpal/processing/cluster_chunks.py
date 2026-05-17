"""
Cluster Chunks ideas across podcastsCluster Chunks
✅ Filters low-quality chunks
✅ Preserves full audio metadata (CRITICAL)
✅ Produces clusters ready for real audio blending
"""

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


INPUT_DIR = Path("processed_chunks")
OUTPUT_FILE = Path("clusters.json")

# ✅ Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


# =========================
# LOAD CHUNKS (UPDATED)
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

                    # ✅ IMPORTANT: preserve full metadata
                    all_chunks.append({
                        "podcast": data.get("podcast_id"),
                        "episode": data.get("episode_id"),
                        "text": chunk.get("text"),
                        "tag": chunk.get("tag"),

                        # ✅ NEW (REQUIRED FOR AUDIO CLIPPING)
                        "audio_path": chunk.get("audio_path"),
                        "start": chunk.get("start"),
                        "end": chunk.get("end"),
                    })

    return all_chunks


# =========================
# FILTER HIGH-SIGNAL CHUNKS
# =========================
def filter_chunks(chunks):
    return [
        c for c in chunks
        if c.get("tag") in ("insight", "reflection", "example")
        and c.get("text")
        and len(c["text"].split()) > 20
    ]


# =========================
# CLUSTERING
# =========================
def cluster_chunks(chunks, threshold=0.45):

    # ✅ shorten text for embeddings
    texts = [c["text"][:300] for c in chunks]

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

        # ✅ only meaningful clusters
        if len(cluster) >= 3:
            clusters.append(cluster)

    return clusters


# =========================
# SAVE CLUSTERS (UPDATED)
# =========================
def save_clusters(clusters):

    output = []

    for idx, cluster in enumerate(clusters):

        output.append({
            "cluster_id": idx,

            # ✅ keep full metadata (CRITICAL)
            "items": cluster,

            "cluster_size": len(cluster),
            "sources": list({c["podcast"] for c in cluster}),

            # ✅ keep previews (for debugging)
            "sample_texts": [c["text"] for c in cluster[:3]],
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

