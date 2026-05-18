"""
ingestion_runner Controlled ingestion helper (preview + filtering layer)ingestion_runner.py
✅ Works alongside rss_to_s3 ingestion
✅ Safe RSS parsing
✅ Filters low-quality episodes
✅ Produces clean audio URL list (optional use)
"""

from typing import List, Dict
from podpal.topics.master_topic_podcasters import iter_ingestible_podcasters
from podpal.services.rss_test import fetch_rss_feed


# -------------------------------------------------
# ✅ FILTER (CONTENT QUALITY CONTROL)
# -------------------------------------------------
BAD_TERMS = [
    "mindset", "productivity", "success",
    "motivation", "habits", "self help",
    "relationship", "spiritual", "lifestyle"
]


def is_valid_episode(ep: Dict) -> bool:
    title = ep.get("title", "") or ""
    summary = ep.get("summary", "") or ""

    text = f"{title} {summary}".lower()

    return not any(term in text for term in BAD_TERMS)


# -------------------------------------------------
# ✅ SELECT PODCASTERS
# -------------------------------------------------
def select_podcasters() -> List[Dict]:
    selected = []

    for topic, pod in iter_ingestible_podcasters():
        selected.append(pod)

    print(f"\n✅ Selected {len(selected)} ingestible podcasters")
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

        if not rss:
            return []

        # ✅ handle both possible structures
        items = rss.get("items") or rss.get("entries") or []

        return items

    except Exception as e:
        print(f"⚠️ RSS failed: {podcaster.get('name')} → {e}")
        return []


# -------------------------------------------------
# ✅ EXTRACT AUDIO URLS (ROBUST VERSION)
# -------------------------------------------------
def extract_audio_urls(episodes: List[Dict], max_episodes: int) -> List[str]:

    urls = []

    for ep in episodes:

        if len(urls) >= max_episodes:
            break

        if not is_valid_episode(ep):
            continue

        # ✅ Try enclosure first (most reliable)
        enclosure = ep.get("enclosures")
        if isinstance(enclosure, list) and enclosure:
            url = enclosure[0].get("url")
            if isinstance(url, str):
                urls.append(url)
                continue

        # ✅ Fallback: links field
        links = ep.get("links", [])

        if isinstance(links, list):
            for l in links:
                if (
                    isinstance(l, dict)
                    and "audio" in (l.get("type", "") or "")
                ):
                    url = l.get("href")
                    if isinstance(url, str):
                        urls.append(url)
                        break

    return urls


# -------------------------------------------------
# ✅ BUILD INGESTION LIST (DEBUG / PREVIEW TOOL)
# -------------------------------------------------
def build_ingestion_list() -> List[str]:

    podcasters = select_podcasters()

    all_audio_urls = []

    for pod in podcasters:

        episodes = fetch_episodes(pod)

        if not episodes:
            print(f"⚠️ No episodes: {pod.get('name')}")
            continue

        max_eps = pod.get("max_episodes", 10)

        urls = extract_audio_urls(episodes, max_eps)

        print(f"🎧 {pod.get('name')} → {len(urls)} valid episodes")

        all_audio_urls.extend(urls)

    print(f"\n✅ TOTAL AUDIO FILES: {len(all_audio_urls)}")

    return all_audio_urls


# -------------------------------------------------
# ✅ MAIN RUNNER
# -------------------------------------------------
def run():

    print("\n🚀 STARTING INGESTION PREVIEW\n")

    urls = build_ingestion_list()

    print("\n✅ INGESTION PREVIEW COMPLETE\n")

    return urls


# -------------------------------------------------
# ✅ ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    run()

