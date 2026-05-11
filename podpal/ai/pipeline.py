# podpal/ai/pipeline.py

from podpal.ai.labeling import label_cluster
from podpal.ai.narration import generate_narration


def process_clusters(clusters):
    """
    Input:
        clusters = [
            {
                "id": 1,
                "segments": ["...", "..."]
            }
        ]

    Output:
        enriched clusters with labels + narration
    """

    enriched = []

    for cluster in clusters:
        segments = cluster.get("segments", [])

        # ✅ Skip empty clusters
        if not segments:
            continue

        # ✅ Step 1: Label cluster
        label_data = label_cluster(segments)

        # ✅ Fix: GPT may return string instead of JSON
        if not isinstance(label_data, dict):
            label_data = {
                "label": "Unknown Theme",
                "description": str(label_data)
            }

        # ✅ Safe extraction (prevents ALL your current errors)
        label = label_data.get("label", "Unknown Theme")
        description = label_data.get("description", "")

        # ✅ Step 2: Generate narration
        narration = generate_narration(
            label=label,
            description=description,
            segments=segments
        )

        # ✅ Fix: narration should always be string
        if not isinstance(narration, str):
            narration = str(narration)

        # ✅ Final enriched object
        enriched.append({
            "id": cluster.get("id"),
            "label": label,
            "description": description,
            "narration": narration,
            "segments": segments
        })

    return enriched
