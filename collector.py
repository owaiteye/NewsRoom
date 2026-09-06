"""Fetch + normalize items from direct RSS and Google News RSS. Tolerant of dead feeds."""
import re
import time
import urllib.parse
import feedparser
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0 NewsRoomBot/1.0"}
TIMEOUT = 20

# Generic promo / non-story entries that pollute BBC-style feeds
PROMO_PATTERNS = (
    "bbc news app", "tech life", "newscast", "follow us",
    "sign up for", "newsletter", "live blog setup",
    "news template", "template page",
)

def _is_promo(title, link):
    t = (title or "").strip().lower()
    if len(t) < 15:
        return True
    return any(p in t for p in PROMO_PATTERNS)

def normalize_outlet(outlet, fallback=""):
    """Domains ('telegraph.co.uk') -> display names ('Telegraph')."""
    outlet = (outlet or fallback or "").strip()
    if re.match(r"^[\w-]+\.[\w.]+$", outlet or ""):
        outlet = outlet.split(".")[0].replace("-", " ").title()
    return outlet or fallback or "?"

def clean_title(title, outlet):
    """Drop trailing tails (we render the outlet separately):
    ' - Outlet Name' and ' - outlet.domain' alike."""
    title = (title or "").strip()
    if outlet and outlet.lower() not in ("google news", "?"):
        title = re.sub(r"\s+[–—-]\s*" + re.escape(outlet) + r"\s*$",
                       "", title, flags=re.IGNORECASE).strip()
    title = re.sub(r"\s+[–—-]\s*[\w-]+\.[\w.]+\s*$", "", title).strip()
    return title

def _parse_feed(url, name, pillar, trust):
    try:
        resp = requests.get(url, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)
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
            # Google News RSS carries the real outlet in <source>; prefer it over feed name.
            raw_outlet = name
            try:
                src = e.get("source") if isinstance(e, dict) else getattr(e, "source", None)
                if isinstance(src, dict) and src.get("title"):
                    raw_outlet = src["title"].strip()
                elif isinstance(src, str) and src.strip():
                    raw_outlet = src.strip()
            except Exception:
                pass
            outlet = normalize_outlet(raw_outlet, name)
            title = clean_title(title, outlet)
            items.append({
                "title": title, "link": link, "summary": summary,
                "published": published, "ts": ts, "image": image,
                "source": name, "outlet": outlet, "pillar": pillar, "trust": trust,
            })
        return items, None
    except Exception as ex:
        return [], f"{name}: {ex}"

def gnews_url(query):
    q = urllib.parse.quote(f"{query} when:6h")
    return f"https://news.google.com/rss/search?q={q}&hl=en-UG&gl=UG&ceid=UG:en"

def collect(sources):
    from concurrent.futures import ThreadPoolExecutor
    jobs = []
    for s in sources.get("direct_rss", []):
        jobs.append(("direct", s["url"], s["name"], s["pillar"], s.get("trust", 3)))
    for g in sources.get("gnews_queries", []):
        jobs.append(("gnews", gnews_url(g["query"]), g["name"], g["pillar"], g.get("trust", 3)))

    def _one(job):
        kind, url, name, pillar, trust = job
        items, err = _parse_feed(url, name, pillar, trust)
        if kind == "gnews":
            for it in items:
                it["via"] = "Google News"
        return items, err

    all_items, errors = [], []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for items, err in ex.map(_one, jobs):
            all_items += items
            if err:
                errors.append(err)
    # newest first
    all_items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return all_items, errors
