import faiss
import numpy as np
import json
import boto3
import os
from openai import OpenAI

# ✅ CONFIG
INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"
BUCKET = "podblendz-episode-audio"
MODEL = "text-embedding-3-small"

# ✅ Setup clients
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
s3 = boto3.client("s3")

# ✅ Load FAISS index
print("📦 Loading FAISS index...")
index = faiss.read_index(INDEX_FILE)
print("✅ FAISS loaded")

# ✅ Load ID map
with open(ID_MAP_FILE) as f:
    id_map = json.load(f)

print(f"✅ Loaded {len(id_map)} IDs")


# ✅ Fetch segment from S3
def fetch_segment(segment_id):
    """
    segment_id format:
    'segments/file.json_3'
    """

    try:
        parts = segment_id.split("_")
        file_key = "_".join(parts[:-1])
        idx = int(parts[-1])

        response = s3.get_object(Bucket=BUCKET, Key=file_key)
        data = json.loads(response["Body"].read())

        seg = data["segments"][idx]

        return {
            "text": seg.get("text"),
            "start": seg.get("start"),
            "end": seg.get("end"),
            "source": file_key
        }

    except Exception as e:
        print(f"⚠️ Error fetching {segment_id}: {e}")
        return None


# ✅ MAIN SEARCH FUNCTION
def search(query, k=40):
    print(f"\n🔍 Searching FAISS for: {query}")

    # ✅ Step 1 — embed query
    response = client.embeddings.create(
        model=MODEL,
        input=query
    )

    query_vector = np.array(
        [response.data[0].embedding]
    ).astype("float32")

    # ✅ Step 2 — FAISS search
    distances, indices = index.search(query_vector, k)

    results = []

    # ✅ Step 3 — map results back to segments
    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(id_map):
            continue

        segment_id = id_map[idx]

        segment = fetch_segment(segment_id)

        if not segment:
            continue

        results.append({
            **segment,
            "score": float(distances[0][i])
        })

    print(f"✅ Retrieved {len(results)} segments")

    return results
