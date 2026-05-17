"""
blend_engine.py

✅ Builds blended podcast experiences from themes
✅ Uses clusters.json + themes.json
✅ Selects segments from clusters
✅ Produces structured sequence (intro → transitions → clips)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any


CLUSTERS_FILE = Path("clusters.json")
THEMES_FILE = Path("themes.json")


# -------------------------------------------------
# ✅ LOAD DATA
# -------------------------------------------------
def load_clusters() -> List[Dict[str, Any]]:
    with open(CLUSTERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_themes() -> List[Dict[str, Any]]:
    with open(THEMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# ✅ SELECT THEME
# -------------------------------------------------
def select_theme(themes: List[Dict[str, Any]], index: Optional[int] = None) -> Dict[str, Any]:

    if not themes:
        raise ValueError("No themes available")

    # ✅ explicit selection
    if index is not None and 0 <= index < len(themes):
        return themes[index]

    # ✅ fallback → random
    return random.choice(themes)


# -------------------------------------------------
# ✅ FIND CLUSTER BY ID
# -------------------------------------------------
def find_cluster(clusters: List[Dict[str, Any]], theme: Dict[str, Any]) -> Dict[str, Any]:

    cluster_id = theme.get("cluster_id")

    if cluster_id is None:
        raise ValueError("Theme missing cluster_id")

    if cluster_id >= len(clusters):
        raise ValueError("Cluster index out of range")

    return clusters[cluster_id]


# -------------------------------------------------
# ✅ BUILD SEGMENTS FROM CLUSTER
# -------------------------------------------------
def build_audio_plan(cluster: Dict[str, Any], max_segments: int = 3) -> List[Dict[str, Any]]:

    segments: List[Dict[str, Any]] = []

    texts = cluster.get("sample_texts", [])

    for text in texts[:max_segments]:
        segments.append({
            "text": text,
            "podcast": None,   # placeholder (next phase adds mapping)
            "episode": None,
        })

    return segments


# -------------------------------------------------
# ✅ BUILD NARRATIVE
# -------------------------------------------------
def build_narrative(theme: str, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    sequence: List[Dict[str, Any]] = []

    # ✅ INTRO
    sequence.append({
        "type": "intro",
        "text": f"Welcome to PodBlendz. Today we explore {theme}."
    })

    # ✅ BODY
    for i, seg in enumerate(segments):

        if i > 0:
            sequence.append({
                "type": "transition",
                "text": "Building on that idea, we continue."
            })

        sequence.append({
            "type": "clip",
            "content": seg
        })

    return sequence


# -------------------------------------------------
# ✅ MAIN ENTRY
# -------------------------------------------------
def build_blend(theme_index: Optional[int] = None) -> List[Dict[str, Any]]:

    print("\n🎧 BUILDING SEMANTIC BLEND\n")

    clusters = load_clusters()
    themes = load_themes()

    theme = select_theme(themes, theme_index)

    print(f"🎯 Theme: {theme.get('theme')}")

    cluster = find_cluster(clusters, theme)

    segments = build_audio_plan(cluster)

    print(f"✅ Selected {len(segments)} segments")

    sequence = build_narrative(theme.get("theme", "this topic"), segments)

    return sequence


# -------------------------------------------------
# ✅ TEST ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    result = build_blend()

    for step in result:
        print(step)

