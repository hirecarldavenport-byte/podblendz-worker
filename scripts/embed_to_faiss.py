import boto3
import json
import os
import faiss
import numpy as np
from openai import OpenAI
from datetime import datetime

# ✅ --- Setup clients ---
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
s3 = boto3.client("s3")

# ✅ CONFIG
BUCKET = "podblendz-episode-audio"
BATCH_SIZE = 100
MAX_SEGMENTS = 750000   # keep your limit
DIM = 1536

INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"

# ✅ NEW: metadata/versioning
INDEX_METADATA_FILE = "index_metadata.json"
FAILED_SEGMENTS_FILE = "failed_segments.json"

# ✅ NEW: checkpoint frequency
CHECKPOINT_INTERVAL = 10000

# ✅ IMPROVED:
# Using cosine similarity instead of L2
# Better semantic retrieval quality
index = faiss.IndexFlatIP(DIM)

# ✅ ID mapping (FAISS index → your segment ID)
id_map = []

# ✅ NEW: failed segment tracking
failed_segments = []


def get_batches():
    paginator = s3.get_paginator("list_objects_v2")

    batch_texts = []
    batch_ids = []
    total = 0

    for page in paginator.paginate(Bucket=BUCKET, Prefix="segments/"):

        for obj in page.get("Contents", []):

            key = obj["Key"]

            if not key.endswith(".json"):
                continue

            try:
                response = s3.get_object(Bucket=BUCKET, Key=key)
                data = json.loads(response["Body"].read())

            except Exception as e:

                print(f"⚠️ Failed loading file: {key}")
                print(e)

                failed_segments.append({
                    "file": key,
                    "error": str(e),
                    "stage": "file_load"
                })

                continue

            for i, seg in enumerate(data.get("segments", [])):

                text = seg.get("text")

                # ✅ same filtering logic
                if (
                    not text
                    or len(text.strip()) < 40
                    or len(text.split()) < 8
                ):
                    continue

                segment_id = f"{key}_{i}"

                batch_texts.append(text)
                batch_ids.append(segment_id)

                total += 1

                if len(batch_texts) >= BATCH_SIZE:

                    yield batch_texts, batch_ids

                    batch_texts = []
                    batch_ids = []

                if total >= MAX_SEGMENTS:

                    if batch_texts:
                        yield batch_texts, batch_ids

                    print("✅ Reached max segment limit")
                    return

    # ✅ flush final batch
    if batch_texts:
        yield batch_texts, batch_ids


def save_checkpoint(total_processed):

    print("\n💾 Saving checkpoint...")

    # ✅ save FAISS index
    faiss.write_index(index, INDEX_FILE)

    # ✅ save ID map
    with open(ID_MAP_FILE, "w") as f:
        json.dump(id_map, f)

    # ✅ metadata/version info
    metadata = {
        "embedding_model": "text-embedding-3-small",
        "dimension": DIM,
        "distance_metric": "cosine_similarity",
        "normalized_vectors": True,
        "segment_count": total_processed,
        "batch_size": BATCH_SIZE,
        "bucket": BUCKET,
        "created_at": datetime.utcnow().isoformat(),
        "index_type": "IndexFlatIP"
    }

    with open(INDEX_METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

    # ✅ save failures
    with open(FAILED_SEGMENTS_FILE, "w") as f:
        json.dump(failed_segments, f, indent=2)

    print("✅ Checkpoint saved")


def run():

    total_processed = 0

    print("🚀 Starting FAISS ingestion...\n")

    for texts, ids in get_batches():

        print(f"🔄 Embedding {len(texts)} segments...")

        try:

            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )

        except Exception as e:

            print("⚠️ OpenAI embedding failure")
            print(e)

            for failed_id in ids:

                failed_segments.append({
                    "segment_id": failed_id,
                    "error": str(e),
                    "stage": "embedding_generation"
                })

            continue

        # ✅ Convert embeddings to numpy array
        vectors = np.array(
            [emb.embedding for emb in response.data]
        ).astype("float32")

        # ✅ IMPORTANT:
        # Normalize for cosine similarity search
        faiss.normalize_L2(vectors)

        # ✅ Add to FAISS
        index.add(vectors)

        # ✅ Save ID mapping
        id_map.extend(ids)

        total_processed += len(ids)

        print(f"✅ Total indexed: {total_processed}")

        # ✅ NEW:
        # Periodic checkpointing
        if total_processed % CHECKPOINT_INTERVAL == 0:

            save_checkpoint(total_processed)

    print("\n💾 Saving final FAISS index...")

    # ✅ FINAL SAVE
    save_checkpoint(total_processed)

    print("\n✅ Saved:")
    print(f"   - {INDEX_FILE}")
    print(f"   - {ID_MAP_FILE}")
    print(f"   - {INDEX_METADATA_FILE}")
    print(f"   - {FAILED_SEGMENTS_FILE}")

    print(f"\n✅ Final indexed segments: {total_processed}")
    print(f"✅ Failed segments tracked: {len(failed_segments)}")

    print("\n🎯 DONE — FAISS ready!")


if __name__ == "__main__":
    run()
