"""Publish via Telegram Bot HTTP API (no extra deps)."""
import os
import requests

API = "https://api.telegram.org/bot{token}/{method}"

PILLAR_EMOJI = {
    "uganda": "🇺🇬",
    "geopolitics": "🌍",
    "tech": "💻",
    "crypto": "💰",
    "entertainment": "🎬",
}

def _api(token, method, payload, timeout=25):
    r = requests.post(API.format(token=token, method=method), json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def esc(text):
    # Markdown (legacy) escaping for _ * [ ] `
    return (text or "").replace("_", " ").replace("*", " ").replace("[", "(").replace("]", ")").replace("`", "'")

def build_digest(slot_label, date_label, items, summaries):
    lines = [f"🌍 *NEWSROOM — {esc(slot_label)} | {esc(date_label)}*",
             f"_{len(items)} stories • links included_\n"]
    # group by pillar, keep order
    order = ["uganda", "geopolitics", "tech", "crypto", "entertainment"]
    grouped = {p: [] for p in order}
    for it in items:
        grouped.setdefault(it.get("pillar", "geopolitics"), []).append(it)
    n = 1
    top3 = items[:3]
    if top3:
        lines.append("🔥 *TOP 3*")
        for it in top3:
            s = summaries.get(it["link"], it["title"])
            corr = " (2 sources)" if it.get("_corroborated") else ""
            lines.append(f"{n}. {PILLAR_EMOJI.get(it.get('pillar'), '📰')} *{esc(it['title'])}*{esc(corr)}")
            lines.append(f"   {esc(s)} — {esc(it['source'])} [link]({it['link']})")
            n += 1
        lines.append("")
    for p in order:
        lst = [x for x in grouped.get(p, []) if x not in top3]
        if not lst:
            continue
        lines.append(f"{PILLAR_EMOJI.get(p, '📰')} *{p.upper()}*")
        for it in lst:
            s = summaries.get(it["link"], it["title"])
            lines.append(f"• {esc(it['title'])} — {esc(it['source'])} [link]({it['link']})")
        lines.append("")
    lines.append("_#digest • Full stories via links • via NewsRoom_")
    text = "\n".join(lines)
    return text[:3900]  # Telegram 4096 cap with margin

def build_breaking(items, summaries):
    lines = ["🚨 *BREAKING*"]
    for it in items:
        s = summaries.get(it["link"], it["title"])
        lines.append(f"{PILLAR_EMOJI.get(it.get('pillar'), '📰')} *{esc(it['title'])}*")
        lines.append(f"{esc(s)} — {esc(it['source'])} [link]({it['link']})")
    lines.append("_Unverified developing story • follow links • via NewsRoom_")
    return "\n".join(lines)[:3900]

def send(channel, token, text, hero_image="", dry_run=False):
    if dry_run:
        print("── DRY RUN (no post) ──")
        if hero_image:
            print(f"[hero image: {hero_image}]")
        print(text)
        return {"ok": True, "dry_run": True}
    if hero_image:
        try:
            _api(token, "sendPhoto", {
                "chat_id": channel, "photo": hero_image,
                "caption": text[:1000], "parse_mode": "Markdown"})
            return {"ok": True, "via": "photo"}
        except Exception as ex:
            print(f"sendPhoto failed ({ex}), falling back to text with preview");
    return _api(token, "sendMessage", {
        "chat_id": channel, "text": text,
        "parse_mode": "Markdown", "disable_web_page_preview": False})
