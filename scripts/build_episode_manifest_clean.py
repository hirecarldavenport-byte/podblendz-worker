import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import requests
import xml.etree.ElementTree as ET

from tqdm import tqdm
from pathlib import Path

from podpal.master_topic_podcasters import iter_ingestible_podcasters


# =========================
# CONFIG
# =========================

OUTPUT_FILE = "episode_manifest_clean.jsonl"

MAX_EPISODES_PER_PODCAST = 5   # keep small while testing

DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL = "medium"


# =========================
# RSS PARSER
# =========================

def fetch_rss(feed_url: str):
    resp = requests.get(feed_url, timeout=10)
    return ET.fromstring(resp.content)


def extract_episodes(feed_root, podcast_id):
    episodes = []

    for item in feed_root.iter("item"):
        enclosure = item.find("enclosure")

        if enclosure is None:
            continue

        url = enclosure.attrib.get("url")

        if not url or not url.endswith(".mp3"):
            continue

        title_elem = item.find("title")
        title = title_elem.text if title_elem is not None else "Untitled"

        episode_id = f"{podcast_id}_{hash(url)}"

        episodes.append({
            "episode_id": episode_id,
            "title": title,
            "url": url,
        })

    return episodes


# =========================
# MAIN MANIFEST BUILDER
# =========================

def build_manifest():
    manifest_entries = []

    print("🚀 Building manifest from canonical registry...\n")

    for topic, podcaster in iter_ingestible_podcasters():

        feed_url = podcaster.get("feed_url")

        if not feed_url:
            continue

        podcast_id = podcaster["id"]

        print(f"🔍 Fetching: {podcaster['name']}")

        try:
            root = fetch_rss(feed_url)
            episodes = extract_episodes(root, podcast_id)

        except Exception as e:
            print(f"❌ Failed to fetch {podcaster['name']}: {e}")
            continue

        for ep in episodes[:MAX_EPISODES_PER_PODCAST]:

            entry = {
                "episode_id": ep["episode_id"],
                "podcast_id": podcast_id,
                "creator_id": podcast_id,

                "episode_title": ep["title"],
                "published_at": None,

                "audio": {
                    "source_url": ep["url"],
                    "format": "mp3",
                },

                "language": DEFAULT_LANGUAGE,

                "transcription": {
                    "status": "pending",
                    "model_hint": DEFAULT_MODEL,
                },
            }

            manifest_entries.append(entry)

    if not manifest_entries:
        raise RuntimeError("No episodes found from registry.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry) + "\n")

    print("\n✅ Manifest created")
    print(f"✅ Episodes: {len(manifest_entries)}")
    print(f"✅ File: {OUTPUT_FILE}")


# =========================
# ENTRYPOINT
# =========================

if __name__ == "__main__":
    build_manifest()