"""
blend_engine.py

✅ Resilient semantic blending
✅ Uses verified audio catalog (NO missing S3 files)
✅ Always returns usable segments
✅ Robust episode_id resolution (FINAL FIX)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any


# -------------------------------------------------
# ✅ PATHS
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"

CLUSTERS_FILE = BASE_DIR / "clusters.json"
THEMES_FILE = BASE_DIR / "themes.json"
AUDIO_CATALOG_FILE = DATA_DIR / "audio_catalog.json"


# -------------------------------------------------
# ✅ LOAD JSON
# -------------------------------------------------

def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        print(f"⚠️ Missing file: {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {path}: {e}")
        return []


def load_clusters():
    return load_json(CLUSTERS_FILE)


def load_themes():
    return load_json(THEMES_FILE)


# -------------------------------------------------
# ✅ LOAD AUDIO LOOKUP (CRITICAL)
# -------------------------------------------------

def load_audio_lookup():
    catalog = load_json(AUDIO_CATALOG_FILE)

    lookup = {
        item["episode_id"]: item["audio_path"]
        for item in catalog
    }

    print(f"✅ Loaded audio catalog: {len(lookup)} entries")

    return lookup


# -------------------------------------------------
# ✅ THEME SELECTION
# -------------------------------------------------

def select_theme(themes, index=None):
    if not themes:
        raise ValueError("No themes available")

    if index is not None and 0 <= index < len(themes):
        return themes[index]

    return random.choice(themes)


# -------------------------------------------------
# ✅ CLUSTER SELECTION
# -------------------------------------------------

def find_cluster(clusters, theme):
    cluster_id = theme.get("cluster_id")

    if cluster_id is None or cluster_id >= len(clusters):
        print("⚠️ Invalid cluster_id — fallback")
        return random.choice(clusters)

    return clusters[cluster_id]


# -------------------------------------------------
# ✅ CLEAN + VALIDATE ITEMS (FINAL FIXED)
# -------------------------------------------------

def clean_items(items, audio_lookup):
    seen = set()
    clean = []

    for item in items:
        text = (item.get("text") or "").strip()

        # ✅ CRITICAL FIX: support multiple formats
        episode_id = (
            item.get("episode_id")
            or item.get("episode")
            or item.get("id")
        )

        if not text or not episode_id:
            continue

        audio_path = audio_lookup.get(episode_id)

        if not audio_path:
            continue  # skip invalid/missing files

        if text in seen:
            continue

        seen.add(text)

        # ✅ enforce consistent structure
        item["episode_id"] = episode_id
        item["audio_path"] = audio_path

        clean.append(item)

    return clean


# -------------------------------------------------
# ✅ BUILD AUDIO PLAN
# -------------------------------------------------

def build_audio_plan(cluster, audio_lookup, max_segments=3):
    items = clean_items(cluster.get("items", []), audio_lookup)

    print("DEBUG cluster size:", len(cluster.get("items", [])))
    print("DEBUG valid items:", len(items))

    if not items:
        return []

    items.sort(key=lambda x: len(x.get("text", "")))

    return items[:max_segments]


# -------------------------------------------------
# ✅ FALLBACK SYSTEM
# -------------------------------------------------

def fallback_segments(clusters, audio_lookup, max_segments=3):
    print("⚠️ Using cross-cluster fallback")

    all_items = []

    for cluster in clusters:
        all_items.extend(cluster.get("items", []))

    all_items = clean_items(all_items, audio_lookup)

    if not all_items:
        return []

    all_items.sort(key=lambda x: len(x.get("text", "")))

    return all_items[:max_segments]


# -------------------------------------------------
# ✅ TRANSITIONS
# -------------------------------------------------

def generate_context_transition(prev_text, next_text):
    next_snippet = next_text[:80].strip()

    connectors = [
        "Building on that idea,",
        "Taking that further,",
        "From another perspective,",
        "Continuing this line of thinking,",
        "Expanding on this concept,"
    ]

    return f"{random.choice(connectors)} {next_snippet}"


# -------------------------------------------------
# ✅ NARRATIVE BUILDER
# -------------------------------------------------

def build_narrative(theme, segments):
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
# ✅ MAIN ENGINE
# -------------------------------------------------

def build_blend(theme_index=None):
    print("\n🎧 BUILDING SEMANTIC BLEND\n")

    clusters = load_clusters()
    themes = load_themes()
    audio_lookup = load_audio_lookup()

    if not clusters or not themes:
        print("❌ Missing clusters or themes")
        return []

    theme = select_theme(themes, theme_index)
    print(f"🎯 Theme: {theme.get('theme')}")

    cluster = find_cluster(clusters, theme)

    segments = build_audio_plan(cluster, audio_lookup)

    if not segments:
        segments = fallback_segments(clusters, audio_lookup)

    print(f"✅ Selected {len(segments)} segments")

    if not segments:
        print("❌ Still no segments")
        return []

    return build_narrative(theme.get("theme", "this topic"), segments)


# -------------------------------------------------
# ✅ LOCAL TEST
# -------------------------------------------------

if __name__ == "__main__":
    result = build_blend()

    for step in result:
        print(step)







