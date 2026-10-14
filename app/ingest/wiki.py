import json
import time
from pathlib import Path

import requests

API = "https://minecraft.wiki/api.php"
HEADERS = {"User-Agent": "CraftLore/0.1 (portfolio project; contact: aneeqmalik055@gmail.com)"}
SEED_FILE = Path("data/seed_titles.txt")
RAW_DIR = Path("data/raw")


def fetch_page(title: str) -> dict | None:
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        return None
    return {"title": data["parse"]["title"], "wikitext": data["parse"]["wikitext"]}


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    titles = [
        line.strip()
        for line in SEED_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    failed = []
    for title in titles:
        page = fetch_page(title)
        if page is None:
            failed.append(title)
            print(f"FAILED  {title}")
        else:
            out = RAW_DIR / (page["title"].replace("/", "_").replace(" ", "_") + ".json")
            out.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
            print(f"OK      {page['title']}")
        time.sleep(1)  # be polite to the server

    print(f"\nDone. {len(titles) - len(failed)} saved, {len(failed)} failed.")
    if failed:
        print("Failed titles:", ", ".join(failed))


if __name__ == "__main__":
    main()
