#!/usr/bin/env python3
"""Fetches RSS feeds and writes news.json next to index.html.
Each category can have several URLs - the first one that works is used.
If every URL fails, the old stories from news.json are kept."""
import json, os, re, html, urllib.request
import xml.etree.ElementTree as ET

FEEDS = {
    "games":   ["https://www.gamespot.com/feeds/news/"],
    "movies":  ["https://www.cinemablend.com/rss/topic/news/movies"],
    "tech":    ["https://www.tomshardware.com/feeds.xml"],
    "crypto":  ["https://cointelegraph.com/rss"],
    "various": [
        "https://gizmodo.com/feed",
        "https://gizmodo.com/rss",
        "https://gizmodo.com/rss/",
        "https://io9.gizmodo.com/rss",
        "https://feeds.bbci.co.uk/news/rss.xml",   # last resort so the section is never empty
    ],
}
MAX = 6
FALLBACK_IMG = "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}
NS = {"media": "http://search.yahoo.com/mrss/",
      "content": "http://purl.org/rss/1.0/modules/content/",
      "atom": "http://www.w3.org/2005/Atom"}


def clean(t, n=100):
    t = html.unescape(re.sub(r"<[^>]*>", "", t or "")).strip()
    return t[:n] + "..." if len(t) > n else t


def first_img(t):
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', t or "")
    return m.group(1) if m else ""


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    nodes = root.findall(".//item") or root.findall(".//atom:entry", NS)
    out = []
    for it in nodes[:MAX]:
        title = (it.findtext("title") or it.findtext("atom:title", namespaces=NS) or "Untitled").strip()
        link = (it.findtext("link") or "").strip()
        if not link:
            for le in it.findall("atom:link", NS):
                if le.get("rel", "alternate") == "alternate" and le.get("href"):
                    link = le.get("href"); break
        desc = it.findtext("description") or it.findtext("atom:summary", namespaces=NS) or ""
        full = it.findtext("content:encoded", namespaces=NS) or it.findtext("atom:content", namespaces=NS) or desc
        img = ""
        for tag in ("media:thumbnail", "media:content"):
            e = it.find(tag, NS)
            if e is not None and e.get("url"):
                img = e.get("url"); break
        if not img:
            e = it.find("enclosure")
            if e is not None and e.get("url"):
                img = e.get("url")
        img = img or first_img(full) or first_img(desc) or FALLBACK_IMG
        if link:
            out.append({"title": html.unescape(title), "link": link, "desc": clean(desc or full), "img": img})
    if not out:
        raise ValueError("no items in feed")
    return out


def load_category(urls):
    errors = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                return parse(r.read()), url
        except Exception as e:
            errors.append(f"{url} -> {e}")
            print(f"   failed: {url} ({e})")
    return None, errors


old = {}
if os.path.exists("news.json"):
    try:
        with open("news.json", encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = {}

result = {}
for cat, urls in FEEDS.items():
    items, info = load_category(urls)
    if items:
        result[cat] = items
        print(f"{cat}: {len(items)} stories from {info}")
    else:
        result[cat] = old.get(cat, [])
        print(f"{cat}: ALL SOURCES FAILED, kept {len(result[cat])} old stories")

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
