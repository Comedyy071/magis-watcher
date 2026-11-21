#!/usr/bin/env python3
"""Notify when a new Plaza (newnewnew.space) listing appears in Eindhoven.

Plaza loads its listings with JavaScript, so this uses a headless browser.
"""
import json
import os
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# ---------- settings ----------
CITIES = ["Eindhoven"]   # [] = notify for everything the page shows
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "change-me-to-something-random-12345")
URL = ("https://plaza.newnewnew.space/en/availables-places/living-place"
       "#?gesorteerd-op=prijs%2B&locatie=Eindhoven-Nederland%2B-%2BNoord-Brabant")
STATE_FILE = Path(__file__).with_name("plaza_seen.json")
# ------------------------------

JS = """
els => els.map(a => {
  let node = a, best = a;
  while (node.parentElement && node.parentElement.tagName !== 'BODY') {
    node = node.parentElement;
    const hrefs = new Set([...node.querySelectorAll('a[href*="/details/"]')].map(x => x.href));
    if (hrefs.size > 1) break;
    best = node;
  }
  return {url: a.href, text: best.innerText.replace(/\\s+/g, ' ').trim()};
})
"""


def fetch_listings():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        items = page.eval_on_selector_all('a[href*="/details/"]', JS)
        if not items:
            body = page.inner_text("body")
            print("No listing links found. Page text starts with:")
            print(" ".join(body.split())[:600])
        browser.close()
    return {i["url"]: i["text"] for i in items}


def notify(url, text):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=text[:300].encode("utf-8"),
        headers={"Title": "New Plaza listing", "Click": url, "Priority": "high"},
        timeout=30,
    )
    print("Notified:", url)


def main():
    first_run = not STATE_FILE.exists()
    seen = set(json.loads(STATE_FILE.read_text())) if not first_run else set()

    listings = fetch_listings()
    wanted = {
        u: t for u, t in listings.items()
        if not CITIES or any(c.lower() in t.lower() for c in CITIES)
    }
    print(f"Found {len(listings)} listing(s) on page, {len(wanted)} match {CITIES}.")
    for u, t in list(listings.items())[:3]:
        print("  sample:", u, "|", t[:100])

    new = {u: t for u, t in wanted.items() if u not in seen}
    if first_run:
        print(f"First run: remembering {len(wanted)} listing(s), no alerts.")
    else:
        for u, t in new.items():
            notify(u, t)

    STATE_FILE.write_text(json.dumps(sorted(wanted)))
    print(f"{len(new)} new.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
