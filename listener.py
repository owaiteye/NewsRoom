"""V2 Telegram channel listener (read-only user session).
Only runs when API_ID/API_HASH/SESSION_STRING are set. Never posts as you.
V1 runs fine without it (RSS + Google News only).
"""
import os
import re

URL_RE = re.compile(r"https?://[^\s)]+")
LEAD_OUTLET_RE = re.compile(r"^([A-Z][\w&.\-]*(\s+[A-Z][\w&.\-]*)*)\s*\((.+)\)\s*$")

def _clean_text(text):
    """Drop raw URLs (we keep the first as the link) and unwrap 'Outlet (Headline)'.
    Also strip leading emoji/decoration prefixes source channels love
    (e.g. '🇮🇷 🪖 🇮🇷 💥 - Headline' -> 'Headline')."""
    urls = URL_RE.findall(text or "")
    text = URL_RE.sub(" ", text or "")
    text = re.sub(r"\(\s*\)", "", text)  # leftover empty parens after URL strip
    text = re.sub(r"\s+", " ", text).strip()
    m = LEAD_OUTLET_RE.match(text)
    if m:
        text = m.group(3).strip().rstrip(")")
    # strip leading non-alphanumeric decor (flags, bullets, dashes)
    text = re.sub(r"^[^A-Za-z0-9(\[]+", "", text).strip()
    return text, urls

def _cut_words(text, limit=180):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-.") + "…"

def fetch_channel_posts(limit_per_channel=8, max_total=200):
    api_id = os.environ.get("API_ID", "").strip()
    api_hash = os.environ.get("API_HASH", "").strip()
    session = os.environ.get("TELEGRAM_SESSION_STRING", "").strip()
    if not (api_id and api_hash and session):
        print("listener: secrets missing, skipping Telegram channels (V1 mode).")
        return []
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("listener: telethon not installed, skipping.")
        return []
    import yaml
    with open("config/sources.yaml") as f:
        cfg = yaml.safe_load(f)
    channels = cfg.get("telegram_channels", [])
    pillar_of = {c["name"]: c.get("pillar", "geopolitics") for c in channels}
    trust_of = {c["name"]: c.get("trust", 3) for c in channels}
    items = []
    with TelegramClient(StringSession(session), int(api_id), api_hash) as client:
        for c in channels:
            ch = c["name"]
            try:
                msgs = client.get_messages(ch, limit=limit_per_channel)
                for m in msgs or []:
                    raw = (m.text or "").strip()
                    if len(raw) < 40:
                        continue
                    text, found_urls = _clean_text(raw)
                    if len(text) < 30:
                        continue
                    # find first url or link message
                    url = None
                    if m.entities:
                        for e in m.entities:
                            u = getattr(e, "url", None)
                            if u:
                                url = u
                                break
                    link = url or (found_urls[0] if found_urls else None) or f"https://t.me/{ch}/{m.id}"
                    items.append({
                        "title": _cut_words(text, 180).replace("\n", " "),
                        "link": link, "summary": _cut_words(text, 500),
                        "published": str(m.date), "ts": m.date.timestamp(),
                        "image": "", "source": ch,
                        "pillar": pillar_of.get(ch, "geopolitics"),
                        "trust": trust_of.get(ch, 3), "via_channel": True,
                    })
                    if len(items) >= max_total:
                        break
            except Exception as ex:
                # FloodWait means "slow down": stop pulling more channels this run.
                print(f"listener: {ch} failed: {str(ex)[:120]}")
                if "flood" in str(ex).lower() or "wait" in str(type(ex).__name__).lower():
                    print("listener: rate-limited, stopping early (retries next run)")
                    break
            if len(items) >= max_total:
                break
    print(f"listener: collected {len(items)} posts from Telegram channels.")
    return items
