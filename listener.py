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
    text = re.sub(r"[\u200b-\u200f\u2060-\u2064\ufeff]", "", text)  # invisible chars FIRST
    text = re.sub(r"\(\s*\)", "", text)  # leftover empty parens after URL strip
    text = re.sub(r"\s+", " ", text).strip()
    m = LEAD_OUTLET_RE.match(text)
    if m:
        text = m.group(3).strip().rstrip(")")
    # channel artifacts that defeat dedupe: hashtags, "writes X" bylines
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"\s*,?\s*writes\s+[A-Z][\w.\-]*\.?\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # strip leading non-alphanumeric decor (flags, bullets, dashes)
    text = re.sub(r"^[^A-Za-z0-9(\[]+", "", text).strip()
    text = re.sub(r"^[\(\[]+[^A-Za-z0-9(\[]*", "", text).strip()
    # orphan closing paren left by the strips above ("bank ) The..." -> "bank The...")
    io, ic = text.find("("), text.find(")")
    if ic != -1 and (io == -1 or ic < io):
        text = (text[:ic] + text[ic + 1:]).strip()
    if "(" not in text:
        text = text.rstrip(")").strip()
    return re.sub(r"\s+", " ", text).strip(), urls

def _cut_words(text, limit=260):
    text = (text or "").strip()
    # never leave a dangling opening paren at the end
    text = re.sub(r"\s*\(\s*$", "", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-.")
    cut = re.sub(r"\s*\(\s*$", "", cut).strip()
    return cut + "…"

# Channel ad spam (pump schemes, fake giveaways). Legit crypto news stays.
SPAM_PATTERNS = (
    "trade the inevitable", "100x", "moonshot", "moon shot", "presale live",
    "presale is live", "giveaway", "guaranteed profit", "double your money",
    "risk-free profit", "outcome's first", "join the presale",
)

def _is_spam(text):
    t = (text or "").lower()
    return any(p in t for p in SPAM_PATTERNS)

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
                    if len(text) < 30 or _is_spam(text):
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
