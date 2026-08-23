from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =====================================================
# CONFIG
# =====================================================

ARCHIVE_DIR = Path("recovery_data/archive_pages")
OUTPUT_DIR = Path("recovery_data/episode_pages")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64)"
)

TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# =====================================================
# SESSION
# =====================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": USER_AGENT
    }
)


# =====================================================
# HELPERS
# =====================================================

def safe_text(tag):
    if tag is None:
        return None

    return tag.get_text(
        " ",
        strip=True,
    )


def find_meta(soup, *names):

    for name in names:

        tag = soup.find(
            "meta",
            attrs={"property": name},
        )

        if tag and tag.get("content"):
            return tag["content"]

        tag = soup.find(
            "meta",
            attrs={"name": name},
        )

        if tag and tag.get("content"):
            return tag["content"]

    return None


def extract_audio_url(soup):

    # audio tags
    audio = soup.find("audio")

    if audio:
        src = audio.get("src")

        if src:
            return src

    # source tags
    source = soup.find("source")

    if source:
        src = source.get("src")

        if src:
            return src

    # direct mp3 links
    html = str(soup)

    match = re.search(
        r"https?://[^\s\"']+\.mp3",
        html,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0)

    return None


def extract_page_text(soup):

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text[:50000]


# =====================================================
# SCRAPER
# =====================================================

def scrape_episode(
    podcast_id: str,
    url: str,
):

    try:

        response = session.get(
            url,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title = (
            find_meta(
                soup,
                "og:title",
                "twitter:title",
            )
            or safe_text(soup.title)
        )

        description = find_meta(
            soup,
            "og:description",
            "description",
        )

        published = find_meta(
            soup,
            "article:published_time",
            "publish_date",
            "datePublished",
        )

        audio_url = extract_audio_url(
            soup
        )

        page_text = extract_page_text(
            soup
        )

        return {
            "podcast_id": podcast_id,
            "page_url": url,
            "title": title,
            "published": published,
            "audio_url": audio_url,
            "description": description,
            "page_text": page_text,
        }

    except Exception as exc:

        logging.error(
            "%s failed: %s",
            url,
            exc,
        )

        return None


# =====================================================
# PROCESS FILE
# =====================================================

def process_archive_file(
    archive_file: Path,
):

    podcast_id = archive_file.stem

    logging.info(
        "Processing %s",
        podcast_id,
    )

    with open(
        archive_file,
        "r",
        encoding="utf-8",
    ) as f:

        links = json.load(f)

    results = []

    for item in links:

        url = item.get("url")

        if not url:
            continue

        page = scrape_episode(
            podcast_id,
            url,
        )

        if page:
            results.append(page)

    outfile = (
        OUTPUT_DIR /
        f"{podcast_id}.json"
    )

    with open(
        outfile,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    logging.info(
        "Saved %s pages",
        len(results),
    )


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    files = list(
        ARCHIVE_DIR.glob("*.json")
    )

    logging.info(
        "Found %s archive files",
        len(files),
    )

    for file in files:

        process_archive_file(file)