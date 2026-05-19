"""
blend_engine.py

✅ Resilient semantic blending
✅ ALWAYS returns usable segments (cross-cluster fallback)
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
# ✅ FIND CLUSTER (SAFE)
# -------------------------------------------------
def find_cluster(clusters: List[Dict[str, Any]], theme: Dict[str, Any]) -> Dict[str, Any]:
    cluster_id = theme.get("cluster_id")

    if cluster_id is None or cluster_id >= len(clusters):
        print("⚠️ Invalid cluster_id — using fallback cluster")
        return random.choice(clusters)

    return clusters[cluster_id]


# -------------------------------------------------
# ✅ CLEAN + FILTER ITEMS
# -------------------------------------------------
def clean_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    seen = set()
    clean = []

    for item in items:
        text = item.get("text", "").strip()
        audio = item.get("audio_path")

        if not text or not audio:
            continue

        if text in seen:
            continue

        seen.add(text)
        clean.append(item)

    return clean


# -------------------------------------------------
# ✅ BUILD AUDIO PLAN (RESILIENT)
# -------------------------------------------------
def build_audio_plan(cluster: Dict[str, Any], max_segments: int = 3) -> List[Dict[str, Any]]:

    items = clean_items(cluster.get("items", []))

    print("DEBUG cluster size:", len(cluster.get("items", [])))
    print("DEBUG cleaned items:", len(items))

    if not items:
        return []

    # ✅ Sort for narrative (short → long)
    items.sort(key=lambda x: len(x.get("text", "")))

    # ✅ Always return something
    return items[:max_segments]


# -------------------------------------------------
# ✅ CROSS-CLUSTER FALLBACK (CRITICAL FIX)
# -------------------------------------------------
def fallback_segments(clusters: List[Dict[str, Any]], max_segments: int = 3) -> List[Dict[str, Any]]:

    print("⚠️ Using cross-cluster fallback")

    all_items = []

    for cluster in clusters:
        all_items.extend(cluster.get("items", []))

    all_items = clean_items(all_items)

    if not all_items:
        return []

    all_items.sort(key=lambda x: len(x.get("text", "")))

    return all_items[:max_segments]


# -------------------------------------------------
# ✅ CONTEXT TRANSITION
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

    return f"{random.choice(connectors)} {next_snippet}"


# -------------------------------------------------
# ✅ BUILD NARRATIVE
# -------------------------------------------------
def build_narrative(theme: str, segments: List[Dict[str, Any]]):

    sequence = []

    sequence.append({
        "type": "intro",
        "text": f"Welcome to PodBlendz. Today we explore {theme}."
    })

    for i, seg in enumerate(segments):

        if i > 0:
            sequence.append({
                "type": "transition",
                "text": generate_context_transition(
                    segments[i - 1].get("text", ""),
                    seg.get("text", "")
                )
            })

        sequence.append({
            "type": "clip",
            "content": seg
        })

    return sequence


# -------------------------------------------------
# ✅ MAIN ENGINE (FIXED)
# -------------------------------------------------
def build_blend(theme_index: Optional[int] = None):

    print("\n🎧 BUILDING SEMANTIC BLEND\n")

    clusters = load_clusters()
    themes = load_themes()

    theme = select_theme(themes, theme_index)

    print(f"🎯 Theme: {theme.get('theme')}")

    cluster = find_cluster(clusters, theme)

    segments = build_audio_plan(cluster)

    # ✅ CRITICAL FIX: fallback if empty
    if not segments:
        segments = fallback_segments(clusters)

    print(f"✅ Selected {len(segments)} segments")

    if not segments:
        print("❌ Still no segments — data issue")
        return []

    return build_narrative(theme.get("theme", "this topic"), segments)


# -------------------------------------------------
# ✅ TEST
# -------------------------------------------------
if __name__ == "__main__":
    result = build_blend()

    for step in result:
        print(step)






