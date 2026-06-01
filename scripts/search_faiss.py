import faiss
import numpy as np
import json
import boto3
import os
from openai import OpenAI

# =========================
# ✅ CONFIG
# =========================
INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"
BUCKET = "podblendz-episode-audio"
MODEL = "text-embedding-3-small"

# =========================
# ✅ CLIENTS
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
s3 = boto3.client("s3")

# =========================
# ✅ LOAD INDEX
# =========================
print("📦 Loading FAISS index...")
index = faiss.read_index(INDEX_FILE)
print("✅ FAISS loaded")

with open(ID_MAP_FILE) as f:
    id_map = json.load(f)

print(f"✅ Loaded {len(id_map)} IDs")


# =========================
# ✅ HELPERS
# =========================

def generate_presigned_url(key, expiry=3600):
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expiry
        )
    except Exception as e:
        print(f"⚠️ Failed to sign URL: {key}")
        return None


# =========================
# ✅ FETCH SEGMENT
# =========================

def fetch_segment(segment_id):
    """
    segment_id format:
    'segments/file.json_3'
    """

    try:
        parts = segment_id.split("_")
        file_key = "_".join(parts[:-1])
        idx = int(parts[-1])

        # ✅ Load segment file from S3
        response = s3.get_object(Bucket=BUCKET, Key=file_key)
        data = json.loads(response["Body"].read())

        segments = data.get("segments", [])

        if idx >= len(segments):
            return None

        seg = segments[idx]

        text = seg.get("text", "").strip()
        start = seg.get("start")
        end = seg.get("end")

        # ✅ MUST have timestamps
        if start is None or end is None:
            return None

        # ✅ CRITICAL FIX: STOP GUESSING AUDIO PATH
        audio_key = data.get("audio_file") or data.get("audio_s3_key")


        if not audio_key:
            # ✅ No audio mapping available → skip
            print(f"⚠️ Missing audio_file in {file_key}")
            return None

        # ✅ Generate signed URL
        audio_url = generate_presigned_url(audio_key)

        if not audio_url:
            return None

        return {
            "text": text,
            "start": start,
            "end": end,
            "audio_file": audio_url,   # ✅ REAL usable audio link
            "source": file_key
        }

    except Exception as e:
        print(f"⚠️ Error fetching {segment_id}: {e}")
        return None


# =========================
# ✅ SEARCH
# =========================

def search(query, k=40):
    print(f"\n🔍 Searching FAISS for: {query}")

    # -------------------------
    # ✅ Embed Query
    # -------------------------
    response = client.embeddings.create(
        model=MODEL,
        input=query
    )

    query_vector = np.array(
        [response.data[0].embedding]
    ).astype("float32")

    # -------------------------
    # ✅ FAISS Search
    # -------------------------
    distances, indices = index.search(query_vector, k)

    results = []

    # -------------------------
    # ✅ Map Results
    # -------------------------
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

    print(f"✅ Retrieved {len(results)} usable segments")

    return results


