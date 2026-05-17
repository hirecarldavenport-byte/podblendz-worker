"""
blend_engine.py

✅ Builds blended podcast experiences from themes
✅ Uses clusters.json + themes.json
✅ Smart narrative-aware clip selection
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

    if index is not None and 0 <= index < len(themes):
        return themes[index]

    return random.choice(themes)


# -------------------------------------------------
# ✅ FIND CLUSTER
# -------------------------------------------------
def find_cluster(clusters: List[Dict[str, Any]], theme: Dict[str, Any]) -> Dict[str, Any]:

    cluster_id = theme.get("cluster_id")

    if cluster_id is None:
        raise ValueError("Theme missing cluster_id")

    if cluster_id >= len(clusters):
        raise ValueError("Cluster index out of range")

    return clusters[cluster_id]


# -------------------------------------------------
# ✅ SMART AUDIO PLAN (KEY UPGRADE)
# -------------------------------------------------
def build_audio_plan(cluster: Dict[str, Any], max_segments: int = 3) -> List[Dict[str, Any]]:

    items = cluster.get("items", [])

    if not items:
        return []

    # ✅ 1. Remove duplicate texts
    seen = set()
    unique_items = []

    for item in items:
        text = item.get("text", "").strip()

        if text and text not in seen:
            seen.add(text)
            unique_items.append(item)

    # ✅ If already small, return early
    if len(unique_items) <= max_segments:
        return unique_items

    # ✅ 2. Diversify by podcast
    by_podcast = {}
    for item in unique_items:
        p = item.get("podcast", "unknown")
        by_podcast.setdefault(p, []).append(item)

    diversified = []
    for group in by_podcast.values():
        diversified.append(group[0])  # take one per source

    # ✅ fallback if not enough diversity
    if len(diversified) < max_segments:
        diversified = unique_items

    # ✅ 3. sort by text length (proxy for depth)
    diversified.sort(key=lambda x: len(x.get("text", "")))

    # ✅ 4. build story arc
    selected = []

    # beginning → simplest
    selected.append(diversified[0])

    # middle → moderate complexity
    if len(diversified) > 2:
        selected.append(diversified[len(diversified) // 2])
    else:
        selected.append(diversified[1])

    # ending → most detailed
    selected.append(diversified[-1])

    return selected[:max_segments]


# -------------------------------------------------
# ✅ TRANSITIONS (VARIATION)
# -------------------------------------------------
TRANSITIONS = [
    "Building on that idea, we continue.",
    "Taking that further, we explore another perspective.",
    "From a different angle, this idea expands.",
    "Let’s go deeper into that concept.",
]


def get_transition() -> str:
    return random.choice(TRANSITIONS)


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
                "text": get_transition()
            })

        sequence.append({
            "type": "clip",
            "content": seg
        })

    return sequence


# -------------------------------------------------
# ✅ MAIN ENGINE
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


