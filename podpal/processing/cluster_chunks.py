"""
cluster_chunks.py

✅ Groups similar ideas across podcasts
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
# ✅ LOAD CHUNKS
# =========================
def load_all_chunks():

    if not INPUT_DIR.exists():
        raise FileNotFoundError("❌ processed_chunks/ directory not found")

    all_chunks = []

    for podcast_dir in INPUT_DIR.iterdir():
        if not podcast_dir.is_dir():
            continue

        for file in podcast_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

                for chunk in data.get("chunks", []):

                    text = chunk.get("text")
                    audio_path = chunk.get("audio_path")
                    start = chunk.get("start")
                    end = chunk.get("end")

                    # ✅ STRICT VALIDATION (CRITICAL)
                    if (
                        not text
                        or not audio_path
                        or start is None
                        or end is None
                    ):
                        continue

                    all_chunks.append({
                        "podcast": data.get("podcast_id"),
                        "episode": data.get("episode_id"),
                        "text": text.strip(),
                        "tag": chunk.get("tag"),

                        # ✅ REQUIRED FIELDS
                        "audio_path": audio_path,
                        "start": float(start),
                        "end": float(end),
                    })

    return all_chunks


# =========================
# ✅ FILTER HIGH-SIGNAL CHUNKS
# =========================
def filter_chunks(chunks):

    filtered = []

    for c in chunks:

        text = c.get("text", "")
        tag = c.get("tag")

        if not text:
            continue

        if tag not in ("insight", "reflection", "example"):
            continue

        if len(text.split()) <= 20:
            continue

        filtered.append(c)

    return filtered


# =========================
# ✅ CLUSTERING LOGIC
# =========================
def cluster_chunks(chunks, threshold=0.45):

    if not chunks:
        print("⚠️ No chunks available for clustering")
        return []

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

        # ✅ keep only meaningful groups
        if len(cluster) >= 3:
            clusters.append(cluster)

    return clusters


# =========================
# ✅ SAVE CLUSTERS
# =========================
def save_clusters(clusters):

    output = []

    for idx, cluster in enumerate(clusters):

        output.append({
            "cluster_id": idx,

            # ✅ FULL METADATA (CRITICAL)
            "items": cluster,

            "cluster_size": len(cluster),
            "sources": list({c["podcast"] for c in cluster}),

            # ✅ debugging previews
            "sample_texts": [c["text"] for c in cluster[:3]],
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"✅ [CLUSTER] Saved to {OUTPUT_FILE}")


# =========================
# ✅ MAIN RUNNER
# =========================
def run():

    print("\n🚀 STARTING CLUSTERING PIPELINE\n")

    chunks = load_all_chunks()
    print(f"✅ Loaded {len(chunks)} valid chunks")

    chunks = filter_chunks(chunks)
    print(f"✅ Filtered to {len(chunks)} high-signal chunks")

    clusters = cluster_chunks(chunks)
    print(f"✅ Created {len(clusters)} clusters")

    save_clusters(clusters)

    print("\n✅ CLUSTERING COMPLETE\n")


if __name__ == "__main__":
    run()

