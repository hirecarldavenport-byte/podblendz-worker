import boto3
import json

s3 = boto3.client("s3")
bucket = "podblendz-episode-audio"

paginator = s3.get_paginator("list_objects_v2")

total_segments = 0
total_files = 0

for page in paginator.paginate(Bucket=bucket, Prefix="segments/"):
    for obj in page.get("Contents", []):
        key = obj["Key"]

        if not key.endswith(".json"):
            continue

        data = s3.get_object(Bucket=bucket, Key=key)
        content = json.loads(data["Body"].read())

        total_segments += len(content.get("segments", []))
        total_files += 1

print(f"Files: {total_files}")
print(f"Total segments: {total_segments}")
print(f"Avg per file: {total_segments / total_files:.2f}")