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
# ✅ SETUP CLIENTS
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
s3 = boto3.client("s3")

# =========================
# ✅ LOAD FAISS + MAP
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
    """
    Generate temporary secure URL for audio playback
    """
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expiry
        )
    except Exception as e:
        print(f"⚠️ Failed to sign URL for {key}: {e}")
        return None


def derive_audio_key(file_key):
    """
    Convert transcript path -> audio path

    Example:
    segments/episode123.json -> audio/episode123.mp3
    """
    return file_key.replace("segments/", "audio/").replace(".json", ".mp3")


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

        response = s3.get_object(Bucket=BUCKET, Key=file_key)
        data = json.loads(response["Body"].read())

        segments = data.get("segments", [])
        if idx >= len(segments):
            return None

        seg = segments[idx]

        # ✅ Get timestamps safely
        start = seg.get("start")
        end = seg.get("end")

        if start is None or end is None:
            return None

        # ✅ Resolve audio path
        audio_key = data.get("audio_file")  # preferred (if stored in JSON)

        if not audio_key:
            # fallback: derive from filename
            audio_key = derive_audio_key(file_key)

        # ✅ Generate playable URL
        audio_url = generate_presigned_url(audio_key)

        return {
            "text": seg.get("text"),
            "start": start,
            "end": end,

            # ✅ CRITICAL ADDITION
            "audio_file": audio_url,

            "source": file_key
        }

    except Exception as e:
        print(f"⚠️ Error fetching {segment_id}: {e}")
        return None


# =========================
# ✅ MAIN SEARCH
# =========================

def search(query, k=40):
    print(f"\n🔍 Searching FAISS for: {query}")

    # -------------------------
    # ✅ Step 1 — Embed query
    # -------------------------
    response = client.embeddings.create(
        model=MODEL,
        input=query
    )

    query_vector = np.array(
        [response.data[0].embedding]
    ).astype("float32")

    # -------------------------
    # ✅ Step 2 — FAISS search
    # -------------------------
    distances, indices = index.search(query_vector, k)

    results = []

    # -------------------------
    # ✅ Step 3 — Map results
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

    print(f"✅ Retrieved {len(results)} segments")

    return results

