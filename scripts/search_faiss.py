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

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

s3 = boto3.client("s3")

# =========================
# ✅ LOAD INDEX
# =========================

print("📦 Loading FAISS index...")

index = faiss.read_index(INDEX_FILE)

print("✅ FAISS loaded")

with open(ID_MAP_FILE, "r", encoding="utf-8") as f:
    id_map = json.load(f)

print(f"✅ Loaded {len(id_map)} IDs")

# =========================
# ✅ CACHE
# =========================

segment_cache = {}

# =========================
# ✅ HELPERS
# =========================

def generate_presigned_url(key, expiry=3600):
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
        print(f"⚠️ Failed to sign URL: {key}")
        print(e)
        return None


# =========================
# ✅ LOAD SEGMENT FILE
# =========================

def load_segment_file(file_key):

    if file_key in segment_cache:
        return segment_cache[file_key]

    try:

        response = s3.get_object(
            Bucket=BUCKET,
            Key=file_key
        )

        data = json.loads(
            response["Body"].read()
        )

        segment_cache[file_key] = data

        return data

    except Exception as e:

        print(f"⚠️ Failed loading {file_key}")
        print(e)

        return None


# =========================
# ✅ FETCH SEGMENT
# =========================

def fetch_segment(segment_id):
    """
    Example segment_id:

    segments/file.json_3
    """

    try:

        parts = segment_id.split("_")

        file_key = "_".join(parts[:-1])
        idx = int(parts[-1])

        data = load_segment_file(file_key)

        if not data:
            return None

        segments = data.get("segments", [])

        if idx >= len(segments):
            return None

        seg = segments[idx]

        text = seg.get("text", "").strip()
        start = seg.get("start")
        end = seg.get("end")

        if start is None or end is None:
            return None

        # =========================
        # ✅ AUDIO MAPPING
        # =========================

        audio_key = (
            data.get("audio_file")
            or data.get("audio_s3_key")
        )

        if not audio_key:

            print(
                f"⚠️ Missing audio_file in {file_key}"
            )

            return None

        audio_url = generate_presigned_url(
            audio_key
        )

        if not audio_url:
            return None

        # =========================
        # ✅ PODCAST METADATA
        # =========================

        podcast = data.get("podcast", {})

        return {

            # Clip
            "text": text,
            "start": start,
            "end": end,

            # Audio
            "audio_file": audio_url,
            "source": file_key,

            # Episode Metadata
            "episode_id": data.get("episode_id"),
            "episode_title": data.get("title"),
            "episode_description": data.get("description"),
            "published": data.get("published"),

            # Podcast Metadata
            "podcast_id": podcast.get("id"),
            "podcast_title": podcast.get("title"),
            "podcast_description": podcast.get("description"),
        }

    except Exception as e:

        print(
            f"⚠️ Error fetching {segment_id}: {e}"
        )

        return None


# =========================
# ✅ SEARCH
# =========================

def search(query, k=40):

    print(
        f"\n🔍 Searching FAISS for: {query}"
    )

    # =========================
    # ✅ EMBED QUERY
    # =========================

    response = client.embeddings.create(
        model=MODEL,
        input=query
    )

    query_vector = np.array(
        [response.data[0].embedding]
    ).astype("float32")

    # =========================
    # ✅ FAISS SEARCH
    # =========================

    distances, indices = index.search(
        query_vector,
        k
    )

    results = []

    usable = 0
    skipped = 0

    # =========================
    # ✅ MAP RESULTS
    # =========================

    for i, idx in enumerate(indices[0]):

        if idx < 0 or idx >= len(id_map):
            skipped += 1
            continue

        segment_id = id_map[idx]

        segment = fetch_segment(
            segment_id
        )

        if not segment:
            skipped += 1
            continue

        results.append({
            **segment,
            "score": float(
                distances[0][i]
            )
        })

        usable += 1

    # =========================
    # ✅ DIAGNOSTICS
    # =========================

    print(
        f"✅ Retrieved {usable} usable segments"
    )

    print(
        f"⚠️ Skipped {skipped} segments"
    )

    if results:

        scores = [
            r["score"]
            for r in results
        ]

        print(
            f"📊 Distance range: "
            f"{min(scores):.6f}"
            f" → "
            f"{max(scores):.6f}"
        )

        sample = results[0]

        print("\n✅ Sample Metadata")

        print(
            f"Podcast: "
            f"{sample.get('podcast_title')}"
        )

        print(
            f"Episode: "
            f"{sample.get('episode_title')}"
        )

    return results


