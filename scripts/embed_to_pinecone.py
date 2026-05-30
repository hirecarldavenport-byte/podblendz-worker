import boto3
import json
import os
from openai import OpenAI
from pinecone import Pinecone

# ✅ --- Setup clients ---
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

index = pc.Index("podblendz")

s3 = boto3.client("s3")
BUCKET = "podblendz-episode-audio"

# ✅ Settings (improved)
BATCH_SIZE = 100
MAX_SEGMENTS = 500000 # 🔥 increased for better search quality


def get_batches():
    paginator = s3.get_paginator("list_objects_v2")

    batch_texts = []
    batch_meta = []
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

                # ✅ 🔥 Improved filtering
                if (
                    not text
                    or len(text.strip()) < 40        # longer minimum length
                    or len(text.split()) < 8        # avoid short phrases
                ):
                    continue

                batch_texts.append(text)

                # ✅ metadata remains critical
                batch_meta.append({
                    "id": f"{key}_{i}",
                    "metadata": {
                        "text": text,
                        "start": seg.get("start"),
                        "end": seg.get("end"),
                        "source": key
                    }
                })

                total += 1

                # ✅ yield batch
                if len(batch_texts) >= BATCH_SIZE:
                    yield batch_texts, batch_meta
                    batch_texts = []
                    batch_meta = []

                # ✅ stop early for iteration control
                if total >= MAX_SEGMENTS:
                    if batch_texts:
                        yield batch_texts, batch_meta
                    print("✅ Reached max segment limit")
                    return

    if batch_texts:
        yield batch_texts, batch_meta


def run():
    total_uploaded = 0

    for texts, metadata in get_batches():
        print(f"🔄 Embedding {len(texts)} segments...")

        # ✅ create embeddings
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )

        # ✅ prepare vectors
        vectors = []
        for i, emb in enumerate(response.data):
            vectors.append({
                "id": metadata[i]["id"],
                "values": emb.embedding,
                "metadata": metadata[i]["metadata"]
            })

        print("⬆️ Uploading to Pinecone...")
        index.upsert(vectors=vectors)

        total_uploaded += len(vectors)
        print(f"✅ Total uploaded: {total_uploaded}")

    print("\n🎯 DONE uploading to Pinecone!")


if __name__ == "__main__":
    run()
