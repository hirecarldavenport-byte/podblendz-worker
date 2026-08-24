import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("recovery_data/archive_pages")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def scrape_archive(url, podcast_id):

    print("SCRAPING:", url)

    r = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    for a in soup.find_all("a"):

        href = a.get("href")

        if not isinstance(href, str):
            continue

        href = href.strip()

        if not href:
            continue

        full_url = urljoin(url, href)

        results.append(
            {
                "podcast_id": podcast_id,
                "title": a.get_text(" ", strip=True),
                "url": full_url,
            }
        )

    return results


if __name__ == "__main__":

    targets = [
        ("lex_fridman", "https://lexfridman.com/podcast/"),
        ("econtalk", "https://www.econtalk.org/"),
        ("huberman_lab", "https://www.hubermanlab.com/podcast"),
    ]

    for podcast_id, url in targets:

        data = scrape_archive(url, podcast_id)

        outfile = OUTPUT_DIR / f"{podcast_id}.json"

        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(
            podcast_id,
            "saved",
            len(data),
            "links"
        )