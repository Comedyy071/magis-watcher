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
CITIES = ["Eindhoven"]          # [] = notify for every city
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "change-me-to-something-random-12345")
BASE = "https://magisrealestate.com"
LIST_URL = BASE + "/for-rent?only_available=false"
MAX_PAGES = 5                   # available listings are shown first
STATE_FILE = Path(__file__).with_name("seen.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (personal rental watcher)"}
