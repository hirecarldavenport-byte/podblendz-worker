import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")

url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"

headers = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json"
}

# --------------------------------------
# ✅ DEFINE YOUR EPISODES HERE
# --------------------------------------
episodes = [
    {
        "episode_id": "0023fb72763eb342b835085d38bd0a6e",
        "audio_s3_key": "raw_audio/education_learning/hidden_brain/0023fb72763eb342b835085d38bd0a6e.mp3",
        "language": "en"
    },
    # ✅ add more episodes here
]

# --------------------------------------
# ✅ SEND JOBS
# --------------------------------------
for ep in episodes:
    payload = {
        "input": ep
    }

    print(f"🚀 Sending job for {ep['episode_id']}...")

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"✅ Response: {response.status_code} | {response.text}")