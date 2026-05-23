import json

# load catalog
with open("data/audio_catalog.json") as f:
    catalog = json.load(f)

valid_ids = {item["episode_id"] for item in catalog}

# load original transcription jobs
with open("data/transcription_jobs/education_learning_jobs.json") as f:
    jobs = json.load(f)

filtered = []

for job in jobs:
    episode_id = job.get("episode_id")

    if episode_id in valid_ids:
        filtered.append(job)

print(f"✅ kept {len(filtered)} of {len(jobs)} jobs")

# ✅ THIS is the file your app needs
output_path = "data/transcription_jobs/education_learning_jobs_clean.json"

with open(output_path, "w") as f:
    json.dump(filtered, f, indent=2)

print(f"✅ saved: {output_path}")