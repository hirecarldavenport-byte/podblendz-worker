import boto3
import json
import os
from openai import OpenAI

# --- Setup ---
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
s3 = boto3.client("s3")

BUCKET = "podblendz-episode-audio"

BATCH_SIZE = 100
MAX_SEGMENTS = 2000  # 🔥 change this as needed

def get_segments():
    paginator = s3.get_paginator("list_objects_v2")

    total = 0
    batch = []

    for page in paginator.paginate(Bucket=BUCKET, Prefix="segments/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith(".json"):
                continue

            response = s3.get_object(Bucket=BUCKET, Key=key)
            data = json.loads(response["Body"].read())

            for seg in data.get("segments", []):
                text = seg.get("text")

                if not text or len(text.strip()) < 20:
                    continue  # skip bad segments

                batch.append(text)
                total += 1

                if len(batch) >= BATCH_SIZE:
                    yield batch
                    batch = []

                if total >= MAX_SEGMENTS:
                    if batch:
                        yield batch
                    print("✅ Reached max segment limit")
                    return

    if batch:
        yield batch


def embed_batches():
    total_embedded = 0

    for batch in get_segments():
        print(f"Embedding batch of {len(batch)}...")

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )

        embeddings = [e.embedding for e in response.data]

        total_embedded += len(embeddings)

        print(f"✅ Total embedded: {total_embedded}")

    print("\n🎯 DONE!")
    print(f"Total segments embedded: {total_embedded}")


if __name__ == "__main__":
    embed_batches()