"""
Podcast Feed Ingestion Script

✅ Clean RSS ingestion
✅ Type-safe audio extraction
✅ MP3 validation (no art19, megaphone, etc.)
✅ Duplicate protection
✅ JSONL manifest output
"""

import sys
from pathlib import Path

# ✅ Ensure project root is visible to Python
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import feedparser
import json
import hashlib
from typing import Optional

from config.podcast_registry import PODCAST_REGISTRY


# =========================
# CONFIG
# =========================

OUTPUT_FILE = ROOT_DIR / "manifests" / "episode_manifest_clean.jsonl"

MAX_EPISODES_PER_FEED = 3

BLOCKED_PATTERNS = [
    "art19",
    "megaphone",
    "podtrac",
    "mgln",
]


# =========================
# HELPERS
# =========================

def stable_id(url: str) -> str:
    """Generate stable episode ID"""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def is_valid_audio_url(url: Optional[str]) -> bool:
    """Validate audio URL"""

    if not url:
        return False

    if not isinstance(url, str):
        return False

    if ".mp3" not in url.lower():
        return False

    for bad in BLOCKED_PATTERNS:
        if bad in url.lower():
            return False

    return True


def extract_audio_url(entry) -> Optional[str]:
    """Safely extract audio URL from RSS entry"""

    enclosures = getattr(entry, "enclosures", None)

    if not isinstance(enclosures, list):
        return None

    if len(enclosures) == 0:
        return None

    enclosure = enclosures[0]

    if not isinstance(enclosure, dict):
        return None

    url = enclosure.get("href")

    if not isinstance(url, str):
        return None

    return url


# =========================
# INGESTION CORE
# =========================

def extract_episodes(feed_key: str, feed_url: str) -> list:
    """Extract episodes from a feed"""

    print(f"\n🔍 Processing: {feed_key}")

    feed = feedparser.parse(feed_url)

    episodes = []
    seen_urls = set()

    count = 0

    for entry in feed.entries:

        if count >= MAX_EPISODES_PER_FEED:
            break

        audio_url = extract_audio_url(entry)

        if not is_valid_audio_url(audio_url):
            continue

        # ✅ Guarantee type (fixes Pylance error)
        assert isinstance(audio_url, str)

        if audio_url in seen_urls:
            continue

        seen_urls.add(audio_url)

        episode = {
            "episode_id": f"{feed_key}_{stable_id(audio_url)}",
            "podcast_id": feed_key,
            "episode_title": entry.get("title", ""),
            "audio": {
                "source_url": audio_url,
                "format": "mp3",
            },
            "language": "en",
        }

        episodes.append(episode)
        count += 1

    print(f"✅ Valid episodes found: {len(episodes)}")

    return episodes


# =========================
# MANIFEST BUILDER
# =========================

def build_manifest() -> None:
    """Main ingestion entry point"""

    all_episodes = []

    for key, config in PODCAST_REGISTRY.items():

        feed_url = config["feed_url"]

        episodes = extract_episodes(key, feed_url)

        all_episodes.extend(episodes)

    if not all_episodes:
        print("⚠️ No valid episodes found.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ep in all_episodes:
            f.write(json.dumps(ep) + "\n")

    print("\n✅ Manifest created successfully")
    print(f"📦 Total episodes: {len(all_episodes)}")
    print(f"📁 File: {OUTPUT_FILE}")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    build_manifest()

