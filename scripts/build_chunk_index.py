import json
import boto3
from pathlib import Path

# =====================================================
# CONFIG
# =====================================================

BUCKET = "podblendz-episode-audio"

INPUT_PREFIX = "segments/"
OUTPUT_DIR = Path("chunked_segments")

TARGET_WORDS = 100

s3 = boto3.client("s3")


# =====================================================
# BUILD CHUNKS
# =====================================================

def build_chunks(segments):

    chunks = []

    current_segments = []
    current_words = 0

    for seg in segments:

        text = (seg.get("text") or "").strip()

        if not text:
            continue

        current_segments.append(seg)
        current_words += len(text.split())

        if current_words >= TARGET_WORDS:

            chunks.append(
                create_chunk(current_segments)
            )

            current_segments = []
            current_words = 0

    if current_segments:
        chunks.append(
            create_chunk(current_segments)
        )

    return chunks


def create_chunk(segment_group):

    return {
        "start": float(segment_group[0]["start"]),
        "end": float(segment_group[-1]["end"]),
        "duration": (
            float(segment_group[-1]["end"])
            - float(segment_group[0]["start"])
        ),
        "text": " ".join(
            s["text"].strip()
            for s in segment_group
            if s.get("text")
        ),
        "segment_count": len(segment_group),
    }


# =====================================================
# PROCESS FILE
# =====================================================

def process_file(key):

    obj = s3.get_object(
        Bucket=BUCKET,
        Key=key
    )

    data = json.loads(
        obj["Body"].read()
    )

    segments = data.get("segments", [])

    if not segments:
        return None

    chunks = build_chunks(segments)

    output = {
        **data,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "original_segment_count": len(segments),
    }

    return output


# =====================================================
# SAVE LOCAL FILE
# =====================================================

def save_chunk_file(key, data):

    relative_path = key.replace("segments/", "")

    out_path = OUTPUT_DIR / relative_path

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        out_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2
        )

    return out_path


# =====================================================
# MAIN
# =====================================================

def main():

    print("\n🚀 BUILDING CHUNK TEST DATA\n")

    files = []

    paginator = s3.get_paginator(
        "list_objects_v2"
    )

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=INPUT_PREFIX
    ):
        for obj in page.get(
            "Contents",
            []
        ):
            key = obj["Key"]

            if key.endswith(".json"):
                files.append(key)

    print(
        f"✅ Found {len(files):,} files"
    )

    #
    # Start small
    #
    files = files[:1000]

    print(
        f"✅ Processing {len(files)} files"
    )

    processed = 0

    for key in files:

        try:

            data = process_file(key)

            if not data:
                continue

            out_path = save_chunk_file(
                key,
                data
            )

            processed += 1

            if processed % 10 == 0:
                print(
                    f"✅ Processed {processed}"
                )

        except Exception as e:

            print(
                f"⚠️ Failed: {key}"
            )

            print(e)

    print("\n🎉 COMPLETE")

    print(
        f"Chunk files written to: "
        f"{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()