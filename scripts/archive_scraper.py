from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

OUTPUT_DIR = Path("recovery_data/archive_pages")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_valid_link(href: str) -> bool:
    """
    Filter obvious junk links.
    """

    href = href.strip().lower()

    blocked_prefixes = [
        "#",
        "javascript:",
        "mailto:",
        "tel:",
    ]

    return not any(
        href.startswith(prefix)
        for prefix in blocked_prefixes
    )


def normalize_url(href: str, base_url: str) -> str:
    """
    Convert relative URLs into absolute URLs.
    """
    return urljoin(base_url, href)
def looks_like_episode(url: str) -> bool:

    url = url.lower()

    if "/contact/" in url:
        return False

    if "twitter.com" in url:
        return False

    if "youtube.com" in url:
        return False

    if "apple.com" in url:
        return False

    if "-transcript" in url:
        return True

    return False


def scrape_archive(
    archive_url,
    podcast_id=None,
):
    print("ARCHIVE_URL_RAW:", repr(archive_url))

    logging.info(
        "Scraping %s",
        archive_url,
    )
    """
    Scrape a podcast archive page and return candidate episode links.
    """
    logging.info(
        "Scraping %s",
        archive_url,
    )

    response = requests.get(
        archive_url,
        timeout=DEFAULT_TIMEOUT,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            )
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    links: list[dict] = []
    seen: set[str] = set()

    for a in soup.find_all("a"):

        raw_href = a.get("href")
        if isinstance(raw_href, str):
            print("RAW_HREF:", repr(raw_href))
        break


        if not isinstance(raw_href, str):
            continue

        raw_href = raw_href.strip()

        if raw_href.startswith("<a "):
            continue

        if not is_valid_link(raw_href):
            continue

        href = normalize_url(
            raw_href,
            archive_url,
        )

        if not looks_like_episode(href):
            continue

        if href in seen:
            continue

        text = a.get_text(
            " ",
            strip=True,
        )

        if len(text) < 10:
            continue

        seen.add(href)

        links.append(
            {
                "podcast_id": podcast_id,
                "title": text,
                "url": href,
                "source": "archive_page",
                "confidence": 0.4,
            }
        )

    logging.info(
        "Found %s links",
        len(links),
    )

    return links


def save_results(
    podcast_id: str,
    results: list[dict],
) -> None:
    """
    Save scraped links.
    """

    outfile = OUTPUT_DIR / f"{podcast_id}.json"

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
        "Saved %s results to %s",
        len(results),
        outfile,
    )


if __name__ == "__main__":

    targets = [
        (
            "lex_fridman",
            "https://lexfridman.com/podcast/",
        ),
        (
            "econtalk",
            "https://www.econtalk.org/",
        ),
        (
            "huberman_lab",
            "https://www.hubermanlab.com/podcast",
        ),
    ]

    for podcast_id, archive_url in targets:

        try:

            results = scrape_archive(
                archive_url=archive_url,
                podcast_id=podcast_id,
            )

            save_results(
                podcast_id=podcast_id,
                results=results,
            )

        except Exception as exc:

            logging.exception(
                "%s failed: %s",
                podcast_id,
                exc,
            )