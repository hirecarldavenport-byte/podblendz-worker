"""
blend_engine Builds blended podcast experiences from themesblend_engine.py
✅ Uses clusters.json + themes.json
✅ Story-aware clip selection (progression-based)
✅ Context-aware transitions
✅ ALWAYS returns usable segments (fallback safe)
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
# ✅ SMART AUDIO PLAN (FIXED)
# -------------------------------------------------
def build_audio_plan(cluster: Dict[str, Any], max_segments: int = 3) -> List[Dict[str, Any]]:
    items = cluster.get("items", [])

    if not items:
        return []

    # ✅ 1. Remove duplicates
    seen = set()
    unique_items = []

    for item in items:
        text = item.get("text", "").strip()
        if text and text not in seen:
            seen.add(text)
            unique_items.append(item)

    if not unique_items:
        return []

    # ✅ 2. Sort by length (short → long progression)
    unique_items.sort(key=lambda x: len(x.get("text", "")))

    # ✅ 3. Try to diversify (but DO NOT fail if not possible)
    by_source = {}
    for item in unique_items:
        source = item.get("podcast", "unknown")
        by_source.setdefault(source, []).append(item)

    diversified = [group[0] for group in by_source.values()]

    # ✅ 4. FALLBACK (CRITICAL FIX)
    # If we don't have enough diversity, just use all items
    if len(diversified) < max_segments:
        selected_pool = unique_items
    else:
        selected_pool = diversified

    # ✅ 5. Ensure we always return something
    if len(selected_pool) <= max_segments:
        return selected_pool

    # ✅ 6. Build simple narrative arc
    selected = []

    selected.append(selected_pool[0])                        # intro
    mid_index = len(selected_pool) // 2
    selected.append(selected_pool[mid_index])                # middle
    selected.append(selected_pool[-1])                       # deepest

    return selected[:max_segments]


# -------------------------------------------------
# ✅ CONTEXT-AWARE TRANSITION
# -------------------------------------------------
def generate_context_transition(prev_text: str, next_text: str) -> str:
    next_snippet = next_text[:80].strip()

    connectors = [
        "Building on that idea,",
        "Taking that further,",
        "From another perspective,",
        "Continuing this line of thinking,",
        "Expanding on this concept,",
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

    # ✅ BODY
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

    if not segments:
        print("⚠️ No segments found — returning empty narrative")
        return []

    sequence = build_narrative(theme.get("theme", "this topic"), segments)

    return sequence


# -------------------------------------------------
# ✅ TEST
# -------------------------------------------------
if __name__ == "__main__":
    result = build_blend()

    for step in result:
        print(step)





