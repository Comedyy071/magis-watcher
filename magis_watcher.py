#!/usr/bin/env python3
"""Notify when a new *available* Magis residence appears in the chosen cities.

Setup:
    pip install requests beautifulsoup4
    Install the free ntfy app on your phone, subscribe to a topic name that
    only you know, and put that name in NTFY_TOPIC below.

Run it every 10-15 minutes with cron (see bottom of file).
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---------- settings ----------
CITIES = []          # [] = notify for every city
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "change-me-to-something-random-12345")
BASE = "https://magisrealestate.com"
LIST_URL = BASE + "/for-rent?only_available=false"
MAX_PAGES = 5                   # available listings are shown first
STATE_FILE = Path(__file__).with_name("seen.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (personal rental watcher)"}
# ------------------------------

LISTING_RE = re.compile(r"/for-rent/[^/?#]+/[^/?#]+")


def card_for(link):
    """Walk up from a listing link to the smallest ancestor holding only that listing."""
    node = link
    while node.parent and node.parent.name not in ("body", "html"):
        node = node.parent
        links = {a["href"] for a in node.find_all("a", href=LISTING_RE)}
        if len(links) > 1:
            break
        last_single = node
    return last_single if "last_single" in locals() else link


def fetch_available():
    found = {}
    for page in range(1, MAX_PAGES + 1):
        r = requests.get(LIST_URL, params={"page": page}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        page_has_available = False
        for a in soup.find_all("a", href=LISTING_RE):
            url = urljoin(BASE, a["href"])
            text = " ".join(card_for(a).get_text(" ", strip=True).split())
            if "not available" in text.lower():
                continue
            page_has_available = True
            found[url] = text
        if not page_has_available:
            break
    return found


def notify(url, text):
    title = "New Magis listing"
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=text[:300].encode("utf-8"),
        headers={"Title": title, "Click": url, "Priority": "high"},
        timeout=30,
    )
    print("Notified:", url)


def main():
    first_run = not STATE_FILE.exists()
    seen = set(json.loads(STATE_FILE.read_text())) if not first_run else set()

    available = fetch_available()
    wanted = {
        u: t for u, t in available.items()
        if not CITIES or any(c.lower() in t.lower() for c in CITIES)
    }

    new = {u: t for u, t in wanted.items() if u not in seen}
    if first_run:
        print(f"First run: remembering {len(wanted)} current listing(s), no alerts.")
    else:
        for u, t in new.items():
            notify(u, t)

    # keep only currently-available ones, so a listing that disappears and
    # comes back later triggers a new alert
    STATE_FILE.write_text(json.dumps(sorted(wanted)))
    print(f"{len(wanted)} matching available, {len(new)} new.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)

# Cron example (every 10 minutes, crontab -e):
# */10 * * * * /usr/bin/python3 /path/to/magis_watcher.py >> /path/to/watcher.log 2>&1
