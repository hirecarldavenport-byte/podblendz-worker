import json
import os
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

# =====================================================
# CONFIG
# =====================================================

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

INPUT_DIR = Path("chunked_segments")

BATCH_SIZE = 100
MAX_CHUNKS = 750000

DIM = 1536

INDEX_FILE = "chunk_index.faiss"
ID_MAP_FILE = "chunk_id_map.json"

INDEX_METADATA_FILE = "chunk_index_metadata.json"
FAILED_CHUNKS_FILE = "failed_chunks.json"

CHECKPOINT_INTERVAL = 10000

# =====================================================
# FAISS
# =====================================================

index = faiss.IndexFlatIP(DIM)

id_map = []
failed_chunks = []


# =====================================================
# LOAD CHUNKS
# =====================================================

def get_batches():

    batch_texts = []
    batch_ids = []

    total = 0

    files = list(
        INPUT_DIR.rglob("*.json")
    )

    print(
        f"✅ Found {len(files)} chunk files"
    )

    for file in files:

        try:

            with open(
                file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception as e:

            print(
                f"⚠️ Failed loading {file}"
            )

            failed_chunks.append({
                "file": str(file),
                "error": str(e),
                "stage": "file_load"
            })

            continue

        chunks = data.get(
            "chunks",
            []
        )

        for i, chunk in enumerate(chunks):

            text = (
                chunk.get("text")
                or ""
            ).strip()

            if (
                not text
                or len(text) < 40
                or len(text.split()) < 8
            ):
                continue

            chunk_id = (
                f"{file.as_posix()}_{i}"
            )

            batch_texts.append(text)
            batch_ids.append(chunk_id)

            total += 1

            if len(batch_texts) >= BATCH_SIZE:

                yield (
                    batch_texts,
                    batch_ids
                )

                batch_texts = []
                batch_ids = []

            if total >= MAX_CHUNKS:

                if batch_texts:
                    yield (
                        batch_texts,
                        batch_ids
                    )

                print(
                    "✅ Reached max chunk limit"
                )

                return

    if batch_texts:
        yield (
            batch_texts,
            batch_ids
        )


# =====================================================
# SAVE CHECKPOINT
# =====================================================

def save_checkpoint(total_processed):

    print("\n💾 Saving checkpoint...")

    faiss.write_index(
        index,
        INDEX_FILE
    )

    with open(
        ID_MAP_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            id_map,
            f
        )

    metadata = {
        "embedding_model":
            "text-embedding-3-small",

        "dimension": DIM,

        "distance_metric":
            "cosine_similarity",

        "normalized_vectors":
            True,

        "chunk_count":
            total_processed,

        "batch_size":
            BATCH_SIZE,

        "created_at":
            datetime.utcnow().isoformat(),

        "index_type":
            "IndexFlatIP"
    }

    with open(
        INDEX_METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2
        )

    with open(
        FAILED_CHUNKS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            failed_chunks,
            f,
            indent=2
        )

    print("✅ Checkpoint saved")


# =====================================================
# RUN
# =====================================================

def run():

    total_processed = 0

    print(
        "\n🚀 Starting CHUNK FAISS ingestion\n"
    )

    for texts, ids in get_batches():

        print(
            f"🔄 Embedding {len(texts)} chunks..."
        )

        try:

            response = (
                client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
            )

        except Exception as e:

            print(
                "⚠️ OpenAI embedding failure"
            )

            print(e)

            for failed_id in ids:

                failed_chunks.append({
                    "chunk_id": failed_id,
                    "error": str(e),
                    "stage":
                        "embedding_generation"
                })

            continue

        vectors = np.array(
            [
                emb.embedding
                for emb in response.data
            ]
        ).astype("float32")

        faiss.normalize_L2(vectors)

        index.add(vectors)

        id_map.extend(ids)

        total_processed += len(ids)

        print(
            f"✅ Total indexed: "
            f"{total_processed}"
        )

        if (
            total_processed
            % CHECKPOINT_INTERVAL
            == 0
        ):
            save_checkpoint(
                total_processed
            )

    print(
        "\n💾 Saving final FAISS index..."
    )

    save_checkpoint(
        total_processed
    )

    print("\n✅ Saved:")

    print(
        f"   - {INDEX_FILE}"
    )

    print(
        f"   - {ID_MAP_FILE}"
    )

    print(
        f"   - {INDEX_METADATA_FILE}"
    )

    print(
        f"   - {FAILED_CHUNKS_FILE}"
    )

    print(
        f"\n✅ Final indexed chunks: "
        f"{total_processed}"
    )

    print(
        f"✅ Failed chunks tracked: "
        f"{len(failed_chunks)}"
    )

    print("\n🎯 DONE — Chunk FAISS ready!")


if __name__ == "__main__":
    run()