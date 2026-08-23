import json
import re
from pathlib import Path

ARCHIVE_DIR = Path("recovery_data/archive_pages")

pattern = re.compile(
    r'https?://[^"\',<>\s]+'
)

for file in ARCHIVE_DIR.glob("*.json"):

    with open(file, encoding="utf-8") as f:
        rows = json.load(f)

    fixed = 0

    for row in rows:

        url = row.get("url")

        if not isinstance(url, str):
            continue

        match = pattern.search(url)

        if match:
            row["url"] = match.group(0)
            fixed += 1

    with open(
        file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            rows,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(file.name, fixed)