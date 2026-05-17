"""
theme_extractor.py

✅ Converts clusters → meaningful themes
✅ Safe handling of OpenAI responses
✅ NO crashes from None values
✅ Production-safe fallbacks
"""

import json
import re
from pathlib import Path
from typing import List, Dict

from openai import OpenAI

client = OpenAI()

# ✅ CONFIG
MAX_SAMPLE_CHUNKS = 5
CLUSTER_FILE = Path("clusters.json")
OUTPUT_FILE = Path("themes.json")


# -------------------------------------------------
# ✅ SAFE CLEAN FUNCTION
# -------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\n", " ")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text[:400]


# -------------------------------------------------
# ✅ SAFE THEME GENERATION
# -------------------------------------------------
def generate_theme(sample_texts: List[str]) -> str:
    """
    Convert cluster samples → short theme
    Completely safe (no crashes)
    """

    if not sample_texts:
        return "General topic discussion"

    sample = [clean_text(t) for t in sample_texts[:MAX_SAMPLE_CHUNKS]]

    prompt = f"""
These are excerpts from podcast discussions:

{sample}

Identify ONE clear central idea connecting them.

Return ONLY a short theme (5-10 words).
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        # ✅ SAFE EXTRACTION (NO .strip() UNTIL VERIFIED)
        content = None

        if hasattr(res, "choices") and res.choices:
            choice = res.choices[0]
            if hasattr(choice, "message") and choice.message:
                content = choice.message.content

        if not content:
            print("⚠️ Empty theme response")
            return "General topic discussion"

        clean = content.strip()

        if len(clean) < 5:
            return "General topic discussion"

        return clean[:120]

    except Exception as e:
        print(f"⚠️ Theme generation failed: {e}")
        return "General topic discussion"


# -------------------------------------------------
# ✅ LOAD CLUSTERS
# -------------------------------------------------
def load_clusters():
    if not CLUSTER_FILE.exists():
        raise FileNotFoundError("clusters.json not found")

    with open(CLUSTER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# ✅ BUILD THEME LIBRARY
# -------------------------------------------------
def build_theme_library(clusters: List[Dict]) -> List[Dict]:
    """
    Input: clusters.json structure
    Output: structured theme library
    """

    themes = []

    print("\n🧠 Generating Themes...\n")

    for i, cluster in enumerate(clusters):

        sample_texts = cluster.get("sample_texts", [])

        theme = generate_theme(sample_texts)

        themes.append({
            "cluster_id": i,
            "theme": theme,
            "cluster_size": cluster.get("cluster_size"),
            "sources": cluster.get("sources"),
            "samples": sample_texts,
        })

        print(f"Cluster {i}: {theme}")

    return themes


# -------------------------------------------------
# ✅ SAVE OUTPUT
# -------------------------------------------------
def save_themes(themes: List[Dict]):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(themes, f, indent=2)

    print(f"\n✅ Themes saved to {OUTPUT_FILE}")


# -------------------------------------------------
# ✅ MAIN RUNNER
# -------------------------------------------------
def run():

    print("📦 Loading clusters...")

    clusters = load_clusters()

    print(f"✅ Loaded {len(clusters)} clusters")

    themes = build_theme_library(clusters)

    save_themes(themes)


if __name__ == "__main__":
    run()

