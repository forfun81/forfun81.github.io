#!/usr/bin/env python3
"""Fetches RSS feeds and writes news.json next to index.html.
Run it every 10-15 minutes (cron / Task Scheduler / GitHub Actions)."""
import json, re, html, urllib.request
import xml.etree.ElementTree as ET

FEEDS = {
    "games":   "https://www.gamespot.com/feeds/news/",
    "movies":  "https://www.cinemablend.com/rss/topic/news/movies",
    "tech":    "https://www.tomshardware.com/feeds.xml",
    "crypto":  "https://cointelegraph.com/rss",
    "various": "https://gizmodo.com/feed",
}
MAX = 6
FALLBACK_IMG = "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400"
NS = {"media": "http://search.yahoo.com/mrss/", "content": "http://purl.org/rss/1.0/modules/content/",
      "atom": "http://www.w3.org/2005/Atom"}

def clean(t, n=100):
    t = html.unescape(re.sub(r"<[^>]*>", "", t or "")).strip()
    return t[:n] + "..." if len(t) > n else t

def first_img(t):
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', t or "")
    return m.group(1) if m else ""

def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for it in (root.findall(".//item") or root.findall(".//atom:entry", NS))[:MAX]:
        title = (it.findtext("title") or it.findtext("atom:title", namespaces=NS) or "Untitled").strip()
        link = it.findtext("link") or ""
        if not link.strip():
            le = it.find("atom:link", NS)
            link = le.get("href") if le is not None else "#"
        desc = it.findtext("description") or it.findtext("atom:summary", namespaces=NS) or ""
        full = it.findtext("content:encoded", namespaces=NS) or desc
        img = ""
        for tag in ("media:thumbnail", "media:content"):
            e = it.find(tag, NS)
            if e is not None and e.get("url"):
                img = e.get("url"); break
        if not img:
            e = it.find("enclosure")
            if e is not None and e.get("url"): img = e.get("url")
        img = img or first_img(full) or FALLBACK_IMG
        out.append({"title": html.unescape(title), "link": link.strip(), "desc": clean(desc), "img": img})
    return out

result = {}
for cat, url in FEEDS.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-aggregator)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            result[cat] = parse(r.read())
        print(f"{cat}: {len(result[cat])} stories")
    except Exception as e:
        print(f"{cat}: FAILED ({e})")
        result[cat] = []

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
