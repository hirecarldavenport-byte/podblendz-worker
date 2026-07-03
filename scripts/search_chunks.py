import faiss
import json
import os
from pathlib import Path

import boto3
import numpy as np
from openai import OpenAI

# =====================================================
# CONFIG
# =====================================================

INDEX_FILE = "chunk_index.faiss"
ID_MAP_FILE = "chunk_id_map.json"

CHUNK_DIR = Path("chunked_segments")

BUCKET = "podblendz-episode-audio"

MODEL = "text-embedding-3-small"

# =====================================================
# CLIENTS
# =====================================================

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

s3 = boto3.client("s3")

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
# HELPERS
# =====================================================

def generate_presigned_url(
    key,
    expiry=3600
):

    try:

        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": key
            },
            ExpiresIn=expiry
        )

    except Exception as e:

        print(
            f"⚠️ Failed signing URL: {key}"
        )

        print(e)

        return None


def normalize_podcast(podcast):

    if isinstance(podcast, dict):
        return podcast

    if isinstance(podcast, str):

        return {
            "title": podcast
        }

    return {}

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

    try:

        parts = chunk_id.rsplit("_", 1)

        file_path = parts[0]
        idx = int(parts[1])

        data = load_chunk_file(file_path)

        if not data:
            return None

        chunks = data.get(
            "chunks",
            []
        )

        if idx >= len(chunks):
            return None

        chunk = chunks[idx]

        audio_key = (
            data.get("audio_file")
            or data.get("audio_s3_key")
            or data.get("audio_key")
        )

        audio_url = None

        if audio_key:

            audio_url = generate_presigned_url(
                audio_key
            )

        podcast = normalize_podcast(
            chunk.get("podcast")
            or data.get("podcast")
        )

        return {

            # ---------------------------------
            # Clip Metadata
            # ---------------------------------

            "text": chunk.get("text", ""),
            "start": chunk.get("start"),
            "end": chunk.get("end"),

            # ---------------------------------
            # Chunk Metadata
            # ---------------------------------

            "duration": chunk.get("duration"),
            "segment_count": chunk.get(
                "segment_count"
            ),

            # ---------------------------------
            # Audio
            # ---------------------------------

            "audio_file": audio_url,

            "source": file_path,
            "source_file": file_path,

            # ---------------------------------
            # Episode Metadata
            # ---------------------------------

            "episode_id": (
                chunk.get("episode_id")
                or data.get("episode_id")
            ),

            "episode_title": (
                chunk.get("episode_title")
                or data.get("title")
            ),

            "episode_description":
                data.get("description"),

            "published":
                data.get("published"),

            # ---------------------------------
            # Podcast Metadata
            # ---------------------------------

            "podcast_id":
                podcast.get("id"),

            "podcast_title":
                podcast.get("title"),

            "podcast_description":
                podcast.get("description"),

            "category":
                chunk.get("category")
        }

    except Exception as e:

        print(
            f"⚠️ Failed chunk lookup: "
            f"{chunk_id}"
        )

        print(e)

        return None

# =====================================================
# SEARCH
# =====================================================

def search(query, k=20):

    print(
        f"\n🔍 Searching Chunk Index: {query}"
    )

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

            "score": float(
                distances[0][i]
            )
        })

        usable += 1

    print(
        f"✅ Retrieved {usable} chunks"
    )

    print(
        f"⚠️ Skipped {skipped}"
    )

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

        print("\n✅ Sample Metadata")

        sample = results[0]

        print(
            f"Podcast: "
            f"{sample.get('podcast_title')}"
        )

        print(
            f"Episode: "
            f"{sample.get('episode_title')}"
        )

    return results

# =====================================================
# QUICK TEST
# =====================================================

if __name__ == "__main__":

    results = search(
        "How do great leaders build trust?",
        k=20
    )

    print(
        "\n===== TOP RESULTS =====\n"
    )

    for i, result in enumerate(
        results,
        start=1
    ):

        print(
            f"\n[{i}] "
            f"score={result['score']:.4f}"
        )

        print(
            f"podcast={result.get('podcast_title')}"
        )

        print(
            f"episode={result.get('episode_title')}"
        )

        print(
            f"duration={result.get('duration')}s"
        )

        print(
            result["text"][:500]
        )

        print("-" * 80)