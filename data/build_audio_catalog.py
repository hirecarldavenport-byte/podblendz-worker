import json

BASE_URL = "https://podblendz-episode-audio.s3.us-east-1.amazonaws.com"

# load transcription jobs
with open("data/transcription_jobs/education_learning_jobs.json") as f:
    jobs = json.load(f)

catalog = []

for job in jobs:
    episode_id = job["episode_id"]
    s3_key = job.get("audio_s3_key")

    if not s3_key:
        continue

    catalog.append({
        "episode_id": episode_id,
        "audio_path": f"{BASE_URL}/{s3_key}"
    })

print(f"✅ Built catalog with {len(catalog)} items")

# save
with open("data/audio_catalog.json", "w") as f:
    json.dump(catalog, f, indent=2)

print("✅ Saved data/audio_catalog.json")
