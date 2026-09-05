"""Publish via Telegram Bot HTTP API (no extra deps).

Layout per digest:
  msg 1: hero photo + SHORT caption (header + top story only, <=900 chars)
  msg 2..n: full digest split into <=3800-char chunks, blank line between stories
Breaking: single text message, same chunking.
Per-story icons are country flags (deterministic); section headings keep emojis.
"""
import html as _html
import os
import re
import requests

API = "https://api.telegram.org/bot{token}/{method}"
CHUNK = 3800

PILLAR_EMOJI = {
    "uganda": "🇺🇬",
    "geopolitics": "🌍",
    "tech": "💻",
    "crypto": "💰",
    "entertainment": "🎬",
}
PILLAR_TITLE = {
    "uganda": "UGANDA & REGION",
    "geopolitics": "WORLD & GEOPOLITICS",
    "tech": "TECHNOLOGY",
    "crypto": "CRYPTO & FINANCE",
    "entertainment": "ENTERTAINMENT, SPORT & HEALTH",
}

# Country-flag rules: first match wins. Specific names BEFORE general ones
# ("south sudan" before "sudan", "equatorial guinea" before "guinea", ...).
FLAG_RULES = [
    ("🇺🇬", ("uganda", "kampala", "entebbe", "gulu", "museveni", "updf", "omukama", "ntv uganda", "new vision", "daily monitor", "nilepost", "softpower", "chimpreports", "ug diplomat", "radionetwork")),
    ("🇰🇪", ("kenya", "nairobi", "ruto", "gachagua")),
    ("🇹🇿", ("tanzania", "dodoma", "dar es salaam", "samia suluhu")),
    ("🇷🇼", ("rwanda", "kigali", "kagame")),
    ("🇨🇩", ("democratic republic of congo", "dr congo", "drc", "kinshasa")),
    ("🇨🇬", ("republic of congo", "congo-brazzaville", "brazzaville")),
    ("🇸🇸", ("south sudan", "juba")),
    ("🇧🇮", ("burundi", "gitega", "bujumbura")),
    ("🇿🇲", ("zambia", "lusaka")),
    ("🇿🇼", ("zimbabwe", "harare")),
    ("🇲🇼", ("malawi", "lilongwe")),
    ("🇿🇦", ("south africa", "johannesburg", "pretoria", "cape town", "springboks")),
    ("🇳🇬", ("nigeria", "lagos", "abuja", "tinubu")),
    ("🇬🇭", ("ghana", "accra", "modern ghana")),
    ("🇪🇬", ("egypt", "cairo", "sinai")),
    ("🇪🇹", ("ethiopia", "addis ababa")),
    ("🇸🇴", ("somalia", "mogadishu")),
    ("🇸🇩", ("sudan", "khartoum")),
    ("🇲🇦", ("morocco", "rabat", "casablanca")),
    ("🇩🇿", ("algeria", "algiers")),
    ("🇹🇳", ("tunisia", "tunis")),
    ("🇱🇾", ("libya", "tripoli")),
    ("🇬🇶", ("equatorial guinea", "obiang", "malabo")),
    ("🇬🇳", ("guinea", "conakry")),
    ("🇸🇳", ("senegal", "dakar")),
    ("🇨🇲", ("cameroon", "yaounde")),
    ("🇨🇮", ("ivory coast", "abidjan")),
    ("🇲🇱", ("mali", "bamako")),
    ("🇧🇫", ("burkina faso", "ouagadougou")),
    ("🇳🇪", ("niger", "niamey")),
    ("🇹🇩", ("chad", "n'djamena")),
    ("🇦🇴", ("angola", "luanda")),
    ("🇲🇿", ("mozambique", "maputo")),
    ("🇺🇸", ("united states", "america", "washington", "white house", "pentagon", "cnn", "fox news", "witkoff", "us envoy", "u.s.", "us ")),
    ("🇬🇧", ("britain", "united kingdom", "england", "london", "dover", "bbc", "telegraph", "sky sports", "man city", "arsenal", "chelsea", "aston villa", "coventry", "hull city")),
    ("🇪🇺", ("european union", "brussels", "european commission")),
    ("🇫🇷", ("france", "paris", "macron")),
    ("🇩🇪", ("germany", "berlin", "bundestag", "leipzig")),
    ("🇷🇺", ("russia", "moscow", "putin", "kremlin", "rt news")),
    ("🇺🇦", ("ukraine", "kyiv", "zelensky", "yermak", "budanov")),
    ("🇧🇾", ("belarus", "minsk", "lukashenko")),
    ("🇵🇱", ("poland", "warsaw")),
    ("🇬🇷", ("greece", "athens")),
    ("🇹🇷", ("turkiye", "turkey", "ankara", "erdogan", "fenerbahce")),
    ("🇮🇱", ("israel", "tel aviv", "netanyahu", "jerusalem")),
    ("🇵🇸", ("palestine", "gaza", "west bank", "ramallah", "hamas")),
    ("🇱🇧", ("lebanon", "beirut", "hezbollah")),
    ("🇸🇾", ("syria", "damascus")),
    ("🇾🇪", ("yemen", "taiz", "houthi", "sanaa", "aden")),
    ("🇮🇷", ("iran", "tehran", "khamenei", "bagheri", "okati")),
    ("🇮🇶", ("iraq", "baghdad")),
    ("🇸🇦", ("saudi", "riyadh")),
    ("🇦🇪", ("uae", "dubai", "abu dhabi", "emirates")),
    ("🇶🇦", ("qatar", "doha", "al jazeera")),
    ("🇴🇲", ("oman", "muscat")),
    ("🇰🇼", ("kuwait",)),
    ("🇧🇭", ("bahrain",)),
    ("🇯🇴", ("jordan", "amman")),
    ("🇨🇳", ("china", "beijing", "xinhua", "cgtn")),
    ("🇹🇼", ("taiwan", "taipei")),
    ("🇭🇰", ("hong kong", "scmp")),
    ("🇯🇵", ("japan", "tokyo", "nhk")),
    ("🇰🇵", ("north korea", "pyongyang", "kim jong")),
    ("🇰🇷", ("south korea", "korea", "seoul")),
    ("🇮🇳", ("india", "delhi", "mumbai", "modi")),
    ("🇵🇰", ("pakistan", "islamabad", "karachi")),
    ("🇧🇩", ("bangladesh", "dhaka")),
    ("🇱🇰", ("sri lanka", "colombo")),
    ("🇳🇵", ("nepal", "kathmandu")),
    ("🇲🇲", ("myanmar", "burma", "naypyidaw", "yangon")),
    ("🇹🇭", ("thailand", "bangkok")),
    ("🇻🇳", ("vietnam", "hanoi")),
    ("🇰🇭", ("cambodia", "phnom penh")),
    ("🇮🇩", ("indonesia", "jakarta")),
    ("🇲🇾", ("malaysia", "kuala lumpur")),
    ("🇸🇬", ("singapore", "channelnewsasia")),
    ("🇵🇭", ("philippines", "manila")),
    ("🇦🇺", ("australia", "sydney", "canberra")),
    ("🇳🇿", ("new zealand", "auckland", "wellington", "all blacks")),
    ("🇨🇦", ("canada", "ottawa", "toronto")),
    ("🇲🇽", ("mexico", "mexico city")),
    ("🇧🇷", ("brazil", "brasilia", "sao paulo", "lula")),
    ("🇦🇷", ("argentina", "buenos aires", "milei")),
    ("🇧🇴", ("bolivia", "la paz", "viacha")),
    ("🇨🇱", ("chile", "santiago")),
    ("🇨🇴", ("colombia", "bogota")),
    ("🇻🇪", ("venezuela", "caracas", "maduro")),
    ("🇵🇪", ("peru", "lima")),
    ("🇪🇨", ("ecuador", "quito")),
    ("🇨🇺", ("cuba", "havana")),
    ("🇪🇸", ("spain", "madrid", "barcelona", "hola", "vuelta", "la liga")),
]

# Outlet origin fallback (used only when the text names no country).
OUTLET_FLAGS = {
    "BBC Africa": "🇬🇧", "BBC World": "🇬🇧", "BBC Top": "🇬🇧", "BBC Tech": "🇬🇧",
    "Telegraph": "🇬🇧", "CNA": "🇸🇬", "SCMP": "🇭🇰", "NHK World": "🇯🇵",
    "RT News": "🇷🇺", "rtnews": "🇷🇺", "SputnikInt": "🇷🇺",
    "Daily Monitor": "🇺🇬", "New Vision": "🇺🇬", "NilePost": "🇺🇬",
    "ChimpReports": "🇺🇬", "dailymonitor": "🇺🇬", "africaintel": "🌍",
}

def _word_hit(text, word):
    """Short tokens match whole-word only ('nio' must not fire on 'opinion');
    longer phrases use substring (they already carry context)."""
    w = word.strip()
    if len(w) <= 4:
        return re.search(r"\b" + re.escape(w) + r"s?\b", text) is not None
    return w in text

def story_emoji(it):
    text = f" {(it.get('title') or '')} {(it.get('summary') or '')} ".lower()
    for flag, words in FLAG_RULES:
        if any(_word_hit(text, w) for w in words):
            return flag
    outlet = (it.get("outlet") or it.get("source") or "")
    if outlet in OUTLET_FLAGS:
        return OUTLET_FLAGS[outlet]
    return PILLAR_EMOJI.get(it.get("pillar"), "📰")

def _api(token, method, payload, timeout=25):
    r = requests.post(API.format(token=token, method=method), json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _clean(text):
    text = _html.unescape(text or "")
    return text.replace("\xa0", " ").replace("&nbsp;", " ")

def _outlet(it):
    return it.get("outlet") or it.get("source", "?")

def esc(text):
    return (text or "").replace("_", " ").replace("*", " ").replace("[", "(").replace("]", ")").replace("`", "'")

def cut_words(text, limit):
    """Truncate at a word boundary, never mid-word."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-.") + "…"

def _story_block(num, it, summaries):
    s = summaries.get(it["link"], it["title"])
    corr = " ✅ 2 sources" if it.get("_corroborated") else ""
    src = f" — {_outlet(it)}" if not it.get("via_channel") else f" — via @{it['source']}"
    return (f"{num}. {story_emoji(it)} *{esc(_clean(it['title']))}*{esc(corr)}\n"
            f"   {esc(_clean(cut_words(s, 200)))}{esc(src)} [link]({it['link']})\n")

def pick_hero(items):
    """Prefer images from wires with reliable hotlinking, else first available."""
    trusted = ("BBC", "CNA", "SCMP", "RT", "NHK", "CoinDesk", "Cointelegraph",
               "Telegraph", "AlJazeera", "africaintel", "BellumActaNews")
    for it in items:
        if it.get("image") and str(it.get("source", "")).startswith(trusted):
            return it["image"]
    return next((it.get("image", "") for it in items if it.get("image")), "")

def build_digest_chunks(slot_label, date_label, items, summaries,
                        digest_title="NEWSROOM", header_emoji="🌍", pillars=None):
    header = (f"{header_emoji} *{digest_title} — {esc(slot_label)} | {esc(date_label)}*\n"
              f"_{len(items)} stories • links included_\n")
    order = list(pillars) if pillars else ["uganda", "geopolitics", "tech", "crypto", "entertainment"]
    grouped = {p: [] for p in order}
    for it in items:
        grouped.setdefault(it.get("pillar", "geopolitics"), []).append(it)

    body_blocks = []
    n = 1
    top = items[:3]
    if top:
        body_blocks.append("🔥 *TOP STORIES*\n")
        for it in top:
            body_blocks.append(_story_block(n, it, summaries))
            n += 1
    for p in order:
        rest = [x for x in grouped.get(p, []) if x not in top]
        if not rest:
            continue
        body_blocks.append(f"{PILLAR_EMOJI.get(p, '📰')} *{PILLAR_TITLE.get(p, p.upper())}*\n")
        for it in rest:
            body_blocks.append(_story_block(n, it, summaries))
            n += 1
    body_blocks.append("_#digest • Full stories via links • via NewsRoom_")

    # photo caption: header + top-1 story only (caption cap = 1024)
    first = top[0] if top else items[0]
    caption = (header + f"\n🔥 *TOP STORY*\n" +
               _story_block(1, first, summaries) +
               f"\n_Full {len(items)}-story digest in next message(s) _")
    caption = cut_words(caption, 950)

    # chunk body into messages
    chunks, cur = [], header + "\n"
    for b in body_blocks:
        if len(cur) + len(b) > CHUNK:
            chunks.append(cur)
            cur = f"_(cont. {esc(digest_title)} {esc(slot_label)})_\n\n"
        cur += b + "\n"
    if cur.strip():
        chunks.append(cur)
    return caption, [c[:4000] for c in chunks]

def build_breaking(items, summaries):
    lines = ["🚨 *BREAKING*\n"]
    n = 1
    for it in items:
        s = summaries.get(it["link"], it["title"])
        src = f" — {_outlet(it)}" if not it.get("via_channel") else f" — via @{it['source']}"
        lines.append(f"{story_emoji(it)} *{esc(_clean(it['title']))}*\n"
                     f"   {esc(_clean(cut_words(s, 200)))}{esc(src)} [link]({it['link']})\n")
        n += 1
    lines.append("_Developing story • verify via links • via NewsRoom_")
    text = "\n".join(lines)
    return [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]

def send_digest(channel, token, caption, chunks, hero_image="", dry_run=False):
    if dry_run:
        print("── DRY RUN (no post) ──")
        print(f"[photo: {hero_image or 'none'}]\nCAPTION:\n{caption}\n")
        for i, c in enumerate(chunks, 1):
            print(f"--- MESSAGE {i}/{len(chunks)} ---\n{c}\n")
        return {"ok": True, "dry_run": True, "messages": 1 + len(chunks)}
    sent = []
    if hero_image:
        try:
            sent.append(_api(token, "sendPhoto", {
                "chat_id": channel, "photo": hero_image,
                "caption": caption, "parse_mode": "Markdown"}))
        except Exception as ex:
            print(f"sendPhoto failed ({ex}), posting text only")
    for c in chunks:
        sent.append(_api(token, "sendMessage", {
            "chat_id": channel, "text": c,
            "parse_mode": "Markdown", "disable_web_page_preview": False}))
    return {"ok": True, "messages": len(sent)}

def send_breaking(channel, token, chunks, hero_image="", dry_run=False):
    if dry_run:
        print("── DRY RUN breaking (no post) ──")
        for i, c in enumerate(chunks, 1):
            print(f"--- BREAKING {i}/{len(chunks)} ---\n{c}\n")
        return {"ok": True, "dry_run": True}
    if hero_image:
        try:
            _api(token, "sendPhoto", {
                "chat_id": channel, "photo": hero_image,
                "caption": chunks[0][:1000], "parse_mode": "Markdown"})
            chunks = chunks[1:] if len(chunks) > 1 else []
        except Exception as ex:
            print(f"breaking sendPhoto failed ({ex})")
    for c in chunks:
        _api(token, "sendMessage", {
            "chat_id": channel, "text": c,
            "parse_mode": "Markdown", "disable_web_page_preview": False})
    return {"ok": True}
