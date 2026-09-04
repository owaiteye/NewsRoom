"""Fetch + normalize items from direct RSS and Google News RSS. Tolerant of dead feeds."""
import time
import urllib.parse
import feedparser
import requests

UA = {"User-Agent": "NewsRoomBot/1.0 (+https://t.me/generalintel)"}
TIMEOUT = 20

# Generic promo / non-story entries that pollute BBC-style feeds
PROMO_PATTERNS = (
    "bbc news app", "tech life", "newscast", "follow us",
    "sign up for", "newsletter", "live blog setup",
)

def _is_promo(title, link):
    t = (title or "").strip().lower()
    if len(t) < 25:
        return True
    return any(p in t for p in PROMO_PATTERNS)

def _parse_feed(url, name, pillar, trust):
    try:
        fp = feedparser.parse(url, request_headers=UA)
        items = []
        for e in (fp.entries or [])[:30]:
            link = (getattr(e, "link", "") or "").strip()
            title = (getattr(e, "title", "") or "").strip()
            if not link or not title:
                continue
            if _is_promo(title, link):
                continue
            summary = (getattr(e, "summary", "") or getattr(e, "description", "") or "")[:500]
            published = getattr(e, "published", "") or getattr(e, "updated", "")
            published_parsed = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
            ts = time.mktime(published_parsed) if published_parsed else time.time()
            # feedparser may expose media thumbnail
            image = ""
            try:
                media = getattr(e, "media_thumbnail", None) or getattr(e, "media_content", None)
                if media and isinstance(media, list) and media[0].get("url"):
                    image = media[0]["url"]
            except Exception:
                pass
            items.append({
                "title": title, "link": link, "summary": summary,
                "published": published, "ts": ts, "image": image,
                "source": name, "pillar": pillar, "trust": trust,
            })
        return items, None
    except Exception as ex:
        return [], f"{name}: {ex}"

def gnews_url(query):
    q = urllib.parse.quote(f"{query} when:6h")
    return f"https://news.google.com/rss/search?q={q}&hl=en-UG&gl=UG&ceid=UG:en"

def collect(sources):
    all_items, errors = [], []
    for s in sources.get("direct_rss", []):
        items, err = _parse_feed(s["url"], s["name"], s["pillar"], s.get("trust", 3))
        all_items += items
        if err:
            errors.append(err)
    for g in sources.get("gnews_queries", []):
        items, err = _parse_feed(gnews_url(g["query"]), g["name"], g["pillar"], g.get("trust", 3))
        # tag provenance so digest can show real outlet when possible
        for it in items:
            it["via"] = "Google News"
        all_items += items
        if err:
            errors.append(err)
    # newest first
    all_items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return all_items, errors
