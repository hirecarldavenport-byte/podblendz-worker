"""
submit_runpod_job.py

Send a single test job to RunPod Serverless endpoint.
"""

import os
import sys
import requests


# ---------------------------------------------------
# ✅ ENV HELPERS
# ---------------------------------------------------

def get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"❌ Missing environment variable: {name}")
        sys.exit(1)
    return value


# ---------------------------------------------------
# ✅ MAIN
# ---------------------------------------------------

def main():
    # ✅ Load config
    API_KEY = get_required_env("RUNPOD_API_KEY")
    ENDPOINT_ID = get_required_env("RUNPOD_ENDPOINT_ID")

    url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # ---------------------------------------------------
    # ✅ TEST INPUT (MATCHES YOUR HANDLER EXACTLY)
    # ---------------------------------------------------

    payload = {
        "input": {
            "episode_id": "0023fb72763eb342b835085d38bd0a6e",
            "podcast_id": "hidden_brain",
            "audio_s3_key": "raw_audio/education_learning/hidden_brain/0023fb72763eb342b835085d38bd0a6e.mp3",
            "language": "en"
        }
    }

    # ---------------------------------------------------
    # ✅ SEND JOB
    # ---------------------------------------------------

    print("🚀 Sending job to RunPod...")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print("\n✅ Response:")
        print("Status Code:", response.status_code)
        print(response.text)

        if response.status_code != 200:
            print("⚠️ Warning: Non-200 response")

    except requests.exceptions.RequestException as e:
        print("🔥 Network error:", str(e))


# ---------------------------------------------------

if __name__ == "__main__":
    main()

