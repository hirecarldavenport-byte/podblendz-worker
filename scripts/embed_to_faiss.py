import boto3
import json
import os
import faiss
import numpy as np
from openai import OpenAI

# ✅ --- Setup clients ---
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
s3 = boto3.client("s3")

# ✅ CONFIG
BUCKET = "podblendz-episode-audio"
BATCH_SIZE = 100
MAX_SEGMENTS = 500000   # keep your limit
DIM = 1536

INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"

# ✅ FAISS index
index = faiss.IndexFlatL2(DIM)

# ✅ ID mapping (FAISS index → your segment ID)
id_map = []


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

            response = s3.get_object(Bucket=BUCKET, Key=key)
            data = json.loads(response["Body"].read())

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

    if batch_texts:
        yield batch_texts, batch_ids


def run():
    total_processed = 0

    print("🚀 Starting FAISS ingestion...\n")

    for texts, ids in get_batches():
        print(f"🔄 Embedding {len(texts)} segments...")

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )

        # ✅ Convert embeddings to numpy array
        vectors = np.array(
            [emb.embedding for emb in response.data]
        ).astype("float32")

        # ✅ Add to FAISS
        index.add(vectors)

        # ✅ Save ID mapping
        id_map.extend(ids)

        total_processed += len(ids)

        print(f"✅ Total indexed: {total_processed}")

    print("\n💾 Saving FAISS index...")

    faiss.write_index(index, INDEX_FILE)

    with open(ID_MAP_FILE, "w") as f:
        json.dump(id_map, f)

    print("✅ Saved:")
    print(f"   - {INDEX_FILE}")
    print(f"   - {ID_MAP_FILE}")
    print("\n🎯 DONE — FAISS ready!")


if __name__ == "__main__":
    run()
