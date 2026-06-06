import os
import time
import random
import requests
import boto3
from botocore.exceptions import ClientError
from collections import Counter, defaultdict

# --------------------------------------
# ✅ CONFIG
# --------------------------------------
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "").strip()

DELAY_BETWEEN_JOBS = 2
MAX_EPISODES = 1500

# ✅ NEW — optional diversity control
MAX_PER_PODCAST = 50

S3_BUCKET = "podblendz-episode-audio"
S3_PREFIX = "raw_audio/"

url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"

print("🚀 USING ENDPOINT:", ENDPOINT_ID)
print("🌐 FINAL URL:", url)


headers = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json"
}

s3 = boto3.client("s3")

# --------------------------------------
# ✅ CHECK IF TRANSCRIPT EXISTS
# --------------------------------------
def transcript_exists(category, podcast, episode_id):
    key = f"segments/{category}/{podcast}/{episode_id}.json"

    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


# --------------------------------------
# ✅ FETCH ALL AUDIO FILES
# --------------------------------------
def get_all_episodes():
    print("🔍 Scanning S3 for audio files...")

    paginator = s3.get_paginator("list_objects_v2")
    episodes = []

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith(".mp3"):
                continue

            parts = key.split("/")

            if len(parts) < 4:
                continue

            category, podcast, filename = parts[1], parts[2], parts[3]
            episode_id = filename.replace(".mp3", "")

            episodes.append({
                "episode_id": episode_id,
                "audio_s3_key": key,
                "category": category,
                "podcast": podcast,
                "language": "en"
            })

    print(f"✅ Found {len(episodes)} total audio files")
    return episodes


# --------------------------------------
# ✅ SMART DIVERSIFICATION
# --------------------------------------
def diversify_episodes(episodes, limit):
    print("\n🎯 Diversifying episode selection...")

    # ✅ NEW — randomize first
    random.shuffle(episodes)

    # Group by podcast
    grouped = defaultdict(list)
    for ep in episodes:
        grouped[ep["podcast"]].append(ep)

    # Shuffle each podcast bucket
    for podcast in grouped:
        random.shuffle(grouped[podcast])

    # Round-robin selection
    diversified = []
    podcast_keys = list(grouped.keys())

    while len(diversified) < limit and podcast_keys:
        for podcast in list(podcast_keys):
            if grouped[podcast]:
                diversified.append(grouped[podcast].pop())
                if len(diversified) >= limit:
                    break
            else:
                podcast_keys.remove(podcast)

    print(f"✅ Diversified selection created ({len(diversified)} episodes)")
    return diversified


# --------------------------------------
# ✅ SEND JOB (WITH RETRY)
# --------------------------------------
def send_job(ep):
    payload = {"input": ep}

    print("\n🚀 PAYLOAD BEING SENT:")
    print(payload)

    for attempt in range(3):  # ✅ NEW retry logic
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                print(f"✅ Sent: {ep['episode_id']} | {ep['category']} | {ep['podcast']}")
                return True
            else:
                print(f"⚠️ Attempt {attempt+1} failed: {response.text}")

        except Exception as e:
            print(f"🔥 Attempt {attempt+1} error: {str(e)}")

        time.sleep(2)

    print(f"❌ Final failure: {ep['episode_id']}")
    return False


# --------------------------------------
# ✅ MAIN
# --------------------------------------
def main():
    all_episodes = get_all_episodes()

    print("\n🔍 Filtering out already processed episodes...\n")

    new_episodes = [
        ep for ep in all_episodes
        if not transcript_exists(ep["category"], ep["podcast"], ep["episode_id"])
    ]

    print(f"✅ New episodes available: {len(new_episodes)}")

    # 📊 BEFORE distribution
    counts = Counter(ep["podcast"] for ep in new_episodes)
    print("\n📊 BEFORE distribution (top podcasts):")
    for p, c in counts.most_common(5):
        print(f" - {p}: {c}")

    # ✅ OPTIONAL — enforce per-podcast limit
    podcast_counter = Counter()
    filtered = []

    for ep in new_episodes:
        if podcast_counter[ep["podcast"]] < MAX_PER_PODCAST:
            filtered.append(ep)
            podcast_counter[ep["podcast"]] += 1

    new_episodes = filtered

    # ✅ DIVERSIFY AFTER FILTER
    new_episodes = diversify_episodes(new_episodes, MAX_EPISODES)

    # 📊 AFTER distribution
    counts_after = Counter(ep["podcast"] for ep in new_episodes)
    print("\n📊 AFTER distribution:")
    for p, c in counts_after.most_common():
        print(f" - {p}: {c}")

    print(f"\n⚠️ Processing {len(new_episodes)} episodes...\n")

    for i, ep in enumerate(new_episodes, 1):
        print(f"\n👉 [{i}] {ep['episode_id']} ({ep['podcast']})")

        send_job(ep)

        # ✅ NEW progress tracking
        if i % 50 == 0:
            print(f"\n📊 Progress: {i}/{len(new_episodes)} processed\n")

        time.sleep(DELAY_BETWEEN_JOBS)

    print("\n✅ DONE")


if __name__ == "__main__":
    main()




