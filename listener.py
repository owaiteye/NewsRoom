"""V2 Telegram channel listener (read-only user session).
Only runs when API_ID/API_HASH/SESSION_STRING are set. Never posts as you.
V1 runs fine without it (RSS + Google News only).
"""
import os

def fetch_channel_posts(limit_per_channel=30, max_total=120):
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
    channels = [c["name"] for c in cfg.get("telegram_channels", [])]
    items = []
    with TelegramClient(StringSession(session), int(api_id), api_hash) as client:
        for ch in channels:
            try:
                msgs = client.get_messages(ch, limit=limit_per_channel)
                for m in msgs or []:
                    text = (m.text or "").strip()
                    if len(text) < 40:
                        continue
                    # find first url or link message
                    url = None
                    if m.entities:
                        for e in m.entities:
                            u = getattr(e, "url", None)
                            if u:
                                url = u
                                break
                    link = url or f"https://t.me/{ch}/{m.id}"
                    items.append({
                        "title": text[:160].replace("\n", " "),
                        "link": link, "summary": text[:500],
                        "published": str(m.date), "ts": m.date.timestamp(),
                        "image": "", "source": ch, "pillar": "geopolitics",
                        "trust": 3, "via_channel": True,
                    })
                    if len(items) >= max_total:
                        break
            except Exception as ex:
                print(f"listener: {ch} failed: {ex}")
            if len(items) >= max_total:
                break
    print(f"listener: collected {len(items)} posts from Telegram channels.")
    return items
