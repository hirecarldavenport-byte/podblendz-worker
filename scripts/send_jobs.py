import os
import time
import requests
import boto3
from botocore.exceptions import ClientError
from collections import Counter

# --------------------------------------
# ✅ CONFIG
# --------------------------------------
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")

DELAY_BETWEEN_JOBS = 2
MAX_EPISODES = 3   # ✅ FOR DEBUG (change later)

S3_BUCKET = "podblendz-episode-audio"
S3_PREFIX = "raw_audio/"

url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"

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
# ✅ SEND JOB
# --------------------------------------
def send_job(ep):
    payload = {"input": ep}

    # ✅ DEBUG: show EXACT payload leaving your system
    print("\n🚀 PAYLOAD BEING SENT:")
    print(payload)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sent: {ep['episode_id']} | {ep['category']} | {ep['podcast']}")
            return True
        else:
            print(f"❌ Failed: {ep['episode_id']} | {response.text}")
            return False

    except Exception as e:
        print(f"🔥 Error: {ep['episode_id']} | {str(e)}")
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

    # ✅ Show distribution
    counts = Counter(ep["podcast"] for ep in new_episodes)
    print("\n📊 New episodes by podcast:")
    for p, c in counts.most_common(5):
        print(f" - {p}: {c}")

    # ✅ LIMIT AFTER FILTERING
    new_episodes = new_episodes[:MAX_EPISODES]

    print(f"\n⚠️ Processing {len(new_episodes)} episodes...\n")

    for i, ep in enumerate(new_episodes, 1):
        print(f"\n👉 [{i}] {ep['episode_id']} ({ep['podcast']})")

        send_job(ep)
        time.sleep(DELAY_BETWEEN_JOBS)

    print("\n✅ DONE")


if __name__ == "__main__":
    main()


