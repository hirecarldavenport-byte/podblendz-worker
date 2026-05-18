"""
blend_engine.py

✅ Builds blended podcast experiences from themes
✅ Uses clusters.json + themes.json
✅ Story-aware clip selection (progression-based)
✅ Context-aware transitions (uses clip meaning)
✅ Produces structured sequence for audio rendering
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
# ✅ SMART AUDIO PLAN (STORY-DRIVEN)
# -------------------------------------------------
def build_audio_plan(cluster: Dict[str, Any], max_segments: int = 3) -> List[Dict[str, Any]]:

    items = cluster.get("items", [])

    if not items:
        return []

    # ✅ 1. Remove duplicate text
    seen = set()
    unique_items = []

    for item in items:
        text = item.get("text", "").strip()
        if text and text not in seen:
            seen.add(text)
            unique_items.append(item)

    if len(unique_items) <= max_segments:
        return unique_items

    # ✅ 2. Diversify sources
    by_source = {}
    for item in unique_items:
        source = item.get("podcast", "unknown")
        by_source.setdefault(source, []).append(item)

    diversified = [items[0] for items in by_source.values()]

    if len(diversified) < max_segments:
        diversified = unique_items

    # ✅ 3. Sort by length (proxy for depth progression)
    diversified.sort(key=lambda x: len(x.get("text", "")))

    # ✅ 4. Build narrative arc (simple → mid → deep)
    selected = []

    selected.append(diversified[0])  # introduction idea

    if len(diversified) > 2:
        selected.append(diversified[len(diversified) // 2])
    else:
        selected.append(diversified[1])

    selected.append(diversified[-1])  # most complex

    return selected[:max_segments]


# -------------------------------------------------
# ✅ CONTEXT-AWARE TRANSITION
# -------------------------------------------------
def generate_context_transition(prev_text: str, next_text: str) -> str:

    prev_snippet = prev_text[:80].strip()
    next_snippet = next_text[:80].strip()

    connectors = [
        "Building on that idea,",
        "Taking that further,",
        "From another perspective,",
        "Continuing this line of thinking,",
    ]

    connector = random.choice(connectors)

    return f"{connector} {next_snippet}"


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

    # ✅ BODY WITH CONTEXT TRANSITIONS
    for i, seg in enumerate(segments):

        if i > 0:
            prev_text = segments[i - 1].get("text", "")
            next_text = seg.get("text", "")

            sequence.append({
                "type": "transition",
                "text": generate_context_transition(prev_text, next_text)
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



