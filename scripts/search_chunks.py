import faiss
import json
import os
from pathlib import Path

import numpy as np
from openai import OpenAI

# =====================================================
# CONFIG
# =====================================================

INDEX_FILE = "chunk_index.faiss"
ID_MAP_FILE = "chunk_id_map.json"

CHUNK_DIR = Path("chunked_segments")

MODEL = "text-embedding-3-small"

# =====================================================
# CLIENT
# =====================================================

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# =====================================================
# LOAD INDEX
# =====================================================

print("📦 Loading Chunk FAISS index...")

index = faiss.read_index(INDEX_FILE)

print("✅ Chunk FAISS loaded")

with open(
    ID_MAP_FILE,
    "r",
    encoding="utf-8"
) as f:
    id_map = json.load(f)

print(f"✅ Loaded {len(id_map)} chunk IDs")

# =====================================================
# CACHE
# =====================================================

chunk_cache = {}

# =====================================================
# LOAD FILE
# =====================================================

def load_chunk_file(file_path):

    if file_path in chunk_cache:
        return chunk_cache[file_path]

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        chunk_cache[file_path] = data

        return data

    except Exception as e:

        print(f"⚠️ Failed loading {file_path}")
        print(e)

        return None


# =====================================================
# FETCH CHUNK
# =====================================================

def fetch_chunk(chunk_id):
    """
    Example:

    chunked_segments/business/podcast/episode.json_17
    """

    try:

        parts = chunk_id.rsplit("_", 1)

        file_path = parts[0]
        idx = int(parts[1])

        data = load_chunk_file(file_path)

        if not data:
            return None

        chunks = data.get("chunks", [])

        if idx >= len(chunks):
            return None

        chunk = chunks[idx]

        return {

            # ------------------------------
            # Chunk Content
            # ------------------------------

            "text": chunk.get("text", ""),
            "start": chunk.get("start"),
            "end": chunk.get("end"),
            "duration": chunk.get("duration"),
            "segment_count": chunk.get("segment_count"),

            # ------------------------------
            # Source Metadata
            # ------------------------------

            "episode_id": data.get("episode_id"),
            "podcast_id": data.get("podcast_id"),

            "source_file": file_path
        }

    except Exception as e:

        print(f"⚠️ Failed chunk lookup: {chunk_id}")
        print(e)

        return None


# =====================================================
# SEARCH
# =====================================================

def search(query, k=20):

    print(f"\n🔍 Searching Chunk Index: {query}")

    response = client.embeddings.create(
        model=MODEL,
        input=query
    )

    query_vector = np.array(
        [response.data[0].embedding]
    ).astype("float32")

    faiss.normalize_L2(query_vector)

    distances, indices = index.search(
        query_vector,
        k
    )

    results = []

    usable = 0
    skipped = 0

    for i, idx in enumerate(indices[0]):

        if idx < 0 or idx >= len(id_map):
            skipped += 1
            continue

        chunk_id = id_map[idx]

        chunk = fetch_chunk(chunk_id)

        if not chunk:
            skipped += 1
            continue

        results.append({
            **chunk,
            "score": float(distances[0][i])
        })

        usable += 1

    print(f"✅ Retrieved {usable} chunks")
    print(f"⚠️ Skipped {skipped}")

    if results:

        scores = [
            r["score"]
            for r in results
        ]

        print(
            f"📊 Score range: "
            f"{min(scores):.6f}"
            f" → "
            f"{max(scores):.6f}"
        )

    return results


# =====================================================
# QUICK TEST
# =====================================================

if __name__ == "__main__":

    results = search(
        "mental toughness",
        k=10
    )

    print("\n===== TOP RESULTS =====\n")

    for i, result in enumerate(results, start=1):

        print(
            f"\n[{i}] "
            f"score={result['score']:.4f}"
        )

        print(
            f"podcast={result.get('podcast_id')}"
        )

        print(
            f"duration={result.get('duration')}s"
        )

        print(
            result["text"][:500]
        )

        print("-" * 80)