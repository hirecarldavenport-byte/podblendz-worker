import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("recovery_data/archive_pages")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0 Safari/537.36"
    )
}


def scrape_archive(url, podcast_id):
    print(f"Scraping {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=60,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    results = []
    seen = set()

    for a in soup.find_all("a"):

        href = a.get("href")

        if not isinstance(href, str):
            continue

        href = href.strip()

        if not href:
            continue

        if href.startswith("#"):
            continue

        if href.startswith("javascript:"):
            continue

        full_url = urljoin(url, href)

        if full_url in seen:
            continue

        seen.add(full_url)

        results.append(
            {
                "podcast_id": podcast_id,
                "title": a.get_text(" ", strip=True),
                "url": full_url,
            }
        )

    print(f"Found {len(results)} links")

    return results


if __name__ == "__main__":

    targets = [
        ("lex_fridman", "https://lexfridman.com/podcast/"),
        ("econtalk", "https://www.econtalk.org/"),
        ("huberman_lab", "https://www.hubermanlab.com/podcast"),
    ]

    for podcast_id, url in targets:

        try:

            results = scrape_archive(
                url,
                podcast_id,
            )

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

            print(
                f"Saved {len(results)} links to {outfile}"
            )

        except Exception as exc:

            print(
                f"{podcast_id} failed: {exc}"
            )