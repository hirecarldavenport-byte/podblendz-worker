"""
blend_engine.py

✅ Production-safe semantic blending
✅ Uses transcription_jobs (ground truth segments)
✅ Uses audio_catalog (verified S3 files)
✅ Fully aligned pipeline (FINAL FIX)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any


# -------------------------------------------------
# ✅ PATHS (UPDATED)
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"

# ✅ SWITCHED to clean transcription jobs
JOBS_FILE = DATA_DIR / "transcription_jobs/education_learning_jobs_clean.json"
AUDIO_CATALOG_FILE = DATA_DIR / "audio_catalog.json"

# Themes still optional
THEMES_FILE = BASE_DIR / "themes.json"


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


# -------------------------------------------------
# ✅ LOAD DATA SOURCES
# -------------------------------------------------

def load_jobs():
    jobs = load_json(JOBS_FILE)
    print(f"✅ Loaded jobs: {len(jobs)}")
    return jobs


def load_audio_lookup():
    catalog = load_json(AUDIO_CATALOG_FILE)

    lookup = {
        item["episode_id"]: item["audio_path"]
        for item in catalog
    }

    print(f"✅ Loaded audio catalog: {len(lookup)} entries")

    return lookup


def load_themes():
    return load_json(THEMES_FILE)


# -------------------------------------------------
# ✅ SELECT THEME
# -------------------------------------------------

def select_theme(themes, index=None):
    if not themes:
        return {"theme": "interesting ideas"}

    if index is not None and 0 <= index < len(themes):
        return themes[index]

    return random.choice(themes)


# -------------------------------------------------
# ✅ BUILD SEGMENTS FROM JOBS (CORE CHANGE)
# -------------------------------------------------

def extract_segments(jobs, audio_lookup):
    segments = []

    for job in jobs:
        episode_id = job.get("episode_id")

        if episode_id not in audio_lookup:
            continue

        audio_path = audio_lookup[episode_id]

        # ✅ CRITICAL: detect real segment structure
        raw_segments = (
            job.get("segments")
            or job.get("chunks")
            or job.get("results")
            or []
        )

        for seg in raw_segments:

            # ✅ normalize fields
            text = (
                seg.get("text")
                or seg.get("content")
                or seg.get("transcript")
                or ""
            ).strip()

            if not text:
                continue

            start = (
                seg.get("start")
                or seg.get("start_time")
                or 0
            )

            end = (
                seg.get("end")
                or seg.get("end_time")
                or start + 6
            )

            segments.append({
                "episode_id": episode_id,
                "audio_path": audio_path,
                "text": text,
                "start": start,
                "end": end,
            })

    return segments

# -------------------------------------------------
# ✅ SELECT BEST SEGMENTS
# -------------------------------------------------

def select_segments(segments, max_segments=3):
    if not segments:
        return []

    # Sort by text length (simple quality heuristic)
    segments.sort(key=lambda x: len(x["text"]))

    return segments[:max_segments]


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
# ✅ BUILD NARRATIVE
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
                    segments[i - 1]["text"],
                    seg["text"]
                )
            })

        sequence.append({
            "type": "clip",
            "content": seg
        })

    return sequence


# -------------------------------------------------
# ✅ MAIN ENGINE (FINAL)
# -------------------------------------------------

def build_blend(theme_index=None):
    print("\n🎧 BUILDING SEMANTIC BLEND\n")

    jobs = load_jobs()
    audio_lookup = load_audio_lookup()
    themes = load_themes()

    if not jobs or not audio_lookup:
        print("❌ Missing jobs or audio catalog")
        return []

    theme = select_theme(themes, theme_index)
    print(f"🎯 Theme: {theme.get('theme')}")

    # ✅ CORE: build segments from real data
    segments = extract_segments(jobs, audio_lookup)

    print(f"DEBUG total segments available: {len(segments)}")

    segments = select_segments(segments)

    print(f"✅ Selected {len(segments)} segments")

    if not segments:
        print("❌ No usable segments")
        return []

    return build_narrative(theme.get("theme", "this topic"), segments)


# -------------------------------------------------
# ✅ LOCAL TEST
# -------------------------------------------------

if __name__ == "__main__":
    result = build_blend()

    for step in result:
        print(step)








