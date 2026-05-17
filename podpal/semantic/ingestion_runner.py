"""
ingestion_runner.py

✅ Controlled ingestion using master registry
✅ Respects priority + max_episodes
✅ Safe RSS handling
✅ Filters low-quality / off-topic content
✅ Produces clean audio URL list
"""

from typing import List, Dict

from podpal.topics.master_topic_podcasters import iter_ingestible_podcasters
from podpal.services.rss_test import fetch_rss_feed


# -------------------------------------------------
# ✅ FILTER (PREVENT BAD CONTENT)
# -------------------------------------------------
BAD_TERMS = [
    "mindset", "productivity", "success",
    "motivation", "habits", "self help",
    "relationship", "spiritual", "lifestyle"
]


def is_valid_episode(ep: Dict) -> bool:
    text = (
        (ep.get("title", "") or "") +
        " " +
        (ep.get("summary", "") or "")
    ).lower()

    return not any(term in text for term in BAD_TERMS)


# -------------------------------------------------
# ✅ SELECT PODCASTERS
# -------------------------------------------------
def select_podcasters(priority: str = "high") -> List[Dict]:

    selected = []

    for topic, pod in iter_ingestible_podcasters():

        if pod.get("ingest_priority", "high") == priority:
            selected.append(pod)

    print(f"\n✅ Selected {len(selected)} {priority}-priority podcasters")

    return selected


# -------------------------------------------------
# ✅ FETCH EPISODES
# -------------------------------------------------
def fetch_episodes(podcaster: Dict) -> List[Dict]:

    feed_url = podcaster.get("feed_url")

    if not feed_url:
        return []

    try:
        rss = fetch_rss_feed(feed_url)

        if not rss or "items" not in rss:
            return []

        return rss.get("items", [])

    except Exception as e:
        print(f"⚠️ RSS failed: {podcaster.get('name')} → {e}")
        return []


# -------------------------------------------------
# ✅ EXTRACT AUDIO URLS
# -------------------------------------------------
def extract_audio_urls(episodes: List[Dict], max_episodes: int) -> List[str]:

    urls = []

    for ep in episodes:

        if len(urls) >= max_episodes:
            break

        # ✅ FILTER BAD CONTENT
        if not is_valid_episode(ep):
            continue

        links = ep.get("links", [])

        if not isinstance(links, list):
            continue

        audio_url = next(
            (
                l.get("href")
                for l in links
                if isinstance(l, dict)
                and "audio" in (l.get("type", "") or "")
            ),
            None
        )

        if audio_url:
            urls.append(audio_url)

    return urls


# -------------------------------------------------
# ✅ BUILD INGESTION LIST
# -------------------------------------------------
def build_ingestion_list(priority: str = "high") -> List[str]:

    podcasters = select_podcasters(priority)

    all_audio_urls = []

    for pod in podcasters:

        episodes = fetch_episodes(pod)

        if not episodes:
            continue

        max_eps = pod.get("max_episodes", 10)

        urls = extract_audio_urls(episodes, max_eps)

        print(f"🎧 {pod.get('name')} → {len(urls)} usable episodes")

        all_audio_urls.extend(urls)

    print(f"\n✅ TOTAL AUDIO FILES: {len(all_audio_urls)}")

    return all_audio_urls


# -------------------------------------------------
# ✅ MAIN RUNNER
# -------------------------------------------------
def run(priority: str = "high") -> List[str]:

    print("\n🚀 STARTING INGESTION RUNNER\n")

    audio_urls = build_ingestion_list(priority)

    print("\n✅ INGESTION COMPLETE\n")

    return audio_urls


# -------------------------------------------------
# ✅ ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    run("high")
    print("✅ IMPORT WORKS:", iter_ingestible_podcasters)
