"""
rss_test.py

Purpose:
- Fetch and parse multiple podcast RSS feeds
- Handle SSL issues gracefully (critical fix ✅)
- Normalize podcast and episode metadata
"""

import ssl
import feedparser
from typing import Any, Dict, List, cast


# -------------------------------------------------
# ✅ SSL FIX (CRITICAL)
# -------------------------------------------------

# ✅ This allows feeds with bad SSL certs to still load
ssl._create_default_https_context = ssl._create_unverified_context


# -------------------------------------------------
# CONFIG: RSS FEEDS TO BLEND
# -------------------------------------------------

RSS_URLS = [
    "https://feeds.simplecast.com/54nAGcIl",
    "https://feeds.simplecast.com/T0_zgH_u",
]


# -------------------------------------------------
# ✅ RSS FETCH (UPDATED)
# -------------------------------------------------

def fetch_rss_feed(rss_url: str) -> Dict[str, Any]:
    try:
        feed = feedparser.parse(rss_url)

        # ✅ Debug bad feeds but DON'T break pipeline
        if getattr(feed, "bozo", False):
            print(f"⚠️ RSS feed issue for {rss_url}:")
            print(feed.bozo_exception)

        return {
            "items": feed.entries or [],
            "feed": getattr(feed, "feed", {})
        }

    except Exception as e:
        print(f"🔥 RSS fetch failed for {rss_url}: {e}")
        return {
            "items": [],
            "feed": {}
        }


# -------------------------------------------------
# ✅ DATA NORMALIZATION
# -------------------------------------------------

def extract_podcast_data(feed: Dict[str, Any]) -> Dict[str, Any]:
    podcast: Dict[str, Any] = {
        "title": feed.get("feed", {}).get("title", "").strip(),
        "description": (
            feed.get("feed", {}).get("subtitle")
            or feed.get("feed", {}).get("description", "")
        ).strip(),
        "episodes": []
    }

    for entry in feed.get("items", [])[:5]:
        podcast["episodes"].append({
            "title": entry.get("title", "").strip(),
            "description": entry.get("summary", "").strip(),
            "published": entry.get("published", "N/A"),
        })

    return podcast


# -------------------------------------------------
# ✅ SIMPLE NARRATION (unchanged)
# -------------------------------------------------

def generate_blend_narration(podcasts: List[Dict[str, Any]]) -> str:
    titles = [p["title"] for p in podcasts if p.get("title")]

    if not titles:
        intro = "This blend brings together selected podcast moments."
    elif len(titles) == 1:
        intro = f"This blend brings together moments from {titles[0]}."
    else:
        intro = (
            "This blend brings together moments from "
            + ", ".join(titles[:-1])
            + f", and {titles[-1]}."
        )

    theme = "These podcasts explore ideas shaping modern science and technology."

    return "\n\n".join([
        intro,
        theme,
        "This is your blend."
    ])


# -------------------------------------------------
# ✅ MAIN (TEST EXECUTION)
# -------------------------------------------------

def main() -> None:
    print("Fetching RSS feeds...\n")

    all_podcasts: List[Dict[str, Any]] = []

    for rss_url in RSS_URLS:
        feed = fetch_rss_feed(rss_url)
        podcast_data = extract_podcast_data(feed)
        all_podcasts.append(podcast_data)

    print("\nDEBUG — podcast titles received:")
    for rss_url, podcast in zip(RSS_URLS, all_podcasts):
        print(f"- {rss_url}")
        print(f"  title: '{podcast['title']}'")

    print("\n🗣️ Generated narration:\n")
    print(generate_blend_narration(all_podcasts))


# -------------------------------------------------

if __name__ == "__main__":
    main()