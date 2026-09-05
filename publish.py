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
    ("🇺🇬", ("uganda", "ugandan", "kampala", "entebbe", "gulu", "museveni", "updf", "omukama", "ntv uganda", "new vision", "daily monitor", "nilepost", "softpower", "chimpreports", "ug diplomat", "radionetwork")),
    ("🇰🇪", ("kenya", "kenyan", "nairobi", "ruto", "gachagua")),
    ("🇹🇿", ("tanzania", "tanzanian", "dodoma", "dar es salaam", "samia suluhu")),
    ("🇷🇼", ("rwanda", "rwandan", "kigali", "kagame")),
    ("🇨🇩", ("democratic republic of congo", "dr congo", "drc", "congo", "kinshasa")),
    ("🇨🇬", ("republic of congo", "congo-brazzaville", "brazzaville")),
    ("🇸🇸", ("south sudan", "juba")),
    ("🇧🇮", ("burundi", "gitega", "bujumbura")),
    ("🇿🇲", ("zambia", "lusaka")),
    ("🇿🇼", ("zimbabwe", "harare")),
    ("🇲🇼", ("malawi", "lilongwe")),
    ("🇿🇦", ("south africa", "south african", "johannesburg", "pretoria", "cape town", "springboks")),
    ("🇳🇬", ("nigeria", "lagos", "abuja", "tinubu")),
    ("🇬🇭", ("ghana", "accra", "modern ghana")),
    ("🇪🇬", ("egypt", "egyptian", "cairo", "sinai")),
    ("🇪🇹", ("ethiopia", "ethiopian", "addis ababa")),
    ("🇸🇴", ("somalia", "mogadishu")),
    ("🇸🇩", ("sudan", "sudanese", "khartoum")),
    ("🇲🇦", ("morocco", "rabat", "casablanca")),
    ("🇩🇿", ("algeria", "algiers")),
    ("🇹🇳", ("tunisia", "tunis")),
    ("🇱🇾", ("libya", "tripoli")),
    ("🇬🇶", ("equatorial guinea", "obiang", "malabo")),
    ("🇵🇬", ("papua new guinea", "papua", "port moresby")),
    ("🇬🇼", ("guinea-bissau", "bissau")),
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
    ("🇺🇸", ("united states", "america", "american", "washington", "white house", "pentagon", "cnn", "fox news", "witkoff", "us envoy", "u.s.", "us ", "atlanta")),
    ("🇬🇧", ("britain", "british", "united kingdom", "england", "london", "dover", "bbc", "telegraph", "sky sports", "man city", "arsenal", "chelsea", "aston villa", "coventry", "hull city")),
    ("🇪🇺", ("european union", "european", "brussels", "european commission")),
    ("🇫🇷", ("france", "french", "paris", "macron")),
    ("🇩🇪", ("germany", "german", "berlin", "bundestag", "leipzig")),
    ("🇷🇺", ("russia", "russian", "moscow", "putin", "kremlin", "rt news")),
    ("🇺🇦", ("ukraine", "ukrainian", "kyiv", "zelensky", "yermak", "budanov")),
    ("🇧🇾", ("belarus", "minsk", "lukashenko")),
    ("🇵🇱", ("poland", "polish", "warsaw")),
    ("🇮🇹", ("italy", "italian", "rome", "milan", "meloni")),
    ("🇪🇸", ("spain", "spanish", "madrid", "barcelona", "hola", "vuelta", "la liga")),
    ("🇵🇹", ("portugal", "portuguese", "lisbon")),
    ("🇳🇱", ("netherlands", "dutch", "amsterdam", "hague")),
    ("🇧🇪", ("belgium", "belgian", "brussels")),
    ("🇦🇹", ("austria", "austrian", "vienna")),
    ("🇨🇭", ("switzerland", "swiss", "geneva", "zurich", "bern")),
    ("🇮🇪", ("ireland", "irish", "dublin")),
    ("🇸🇪", ("sweden", "swedish", "stockholm")),
    ("🇳🇴", ("norway", "norwegian", "oslo")),
    ("🇩🇰", ("denmark", "danish", "copenhagen")),
    ("🇫🇮", ("finland", "finnish", "helsinki")),
    ("🇮🇸", ("iceland", "reykjavik")),
    ("🇱🇺", ("luxembourg",)),
    ("🇲🇹", ("malta", "valletta")),
    ("🇨🇾", ("cyprus", "nicosia")),
    ("🇪🇪", ("estonia", "tallinn")),
    ("🇱🇻", ("latvia", "riga")),
    ("🇱🇹", ("lithuania", "vilnius")),
    ("🇵🇱", ("poland", "polish", "warsaw")),
    ("🇨🇿", ("czech", "prague")),
    ("🇸🇰", ("slovakia", "bratislava")),
    ("🇭🇺", ("hungary", "hungarian", "budapest")),
    ("🇷🇴", ("romania", "bucharest")),
    ("🇧🇬", ("bulgaria", "sofia")),
    ("🇬🇷", ("greece", "greek", "athens")),
    ("🇷🇸", ("serbia", "serbian", "belgrade")),
    ("🇭🇷", ("croatia", "croatian", "zagreb")),
    ("🇧🇦", ("bosnia", "sarajevo")),
    ("🇦🇱", ("albania", "tirana")),
    ("🇲🇰", ("macedonia", "skopje")),
    ("🇲🇪", ("montenegro", "podgorica")),
    ("🇸🇮", ("slovenia", "ljubljana")),
    ("🇲🇩", ("moldova", "chisinau")),
    ("🇬🇪", ("georgia", "georgian", "tbilisi")),
    ("🇦🇲", ("armenia", "armenian", "yerevan")),
    ("🇦🇿", ("azerbaijan", "azeri", "baku")),
    ("🇰🇿", ("kazakhstan", "astana", "almaty")),
    ("🇺🇿", ("uzbekistan", "tashkent")),
    ("🇹🇲", ("turkmenistan", "ashgabat")),
    ("🇰🇬", ("kyrgyzstan", "bishkek")),
    ("🇹🇯", ("tajikistan", "dushanbe")),
    ("🇲🇳", ("mongolia", "ulaanbaatar")),
    ("🇦🇫", ("afghanistan", "kabul", "taliban")),
    ("🇹🇷", ("turkiye", "turkey", "turkish", "ankara", "erdogan", "fenerbahce")),
    ("🇮🇱", ("israel", "israeli", "tel aviv", "netanyahu", "jerusalem")),
    ("🇵🇸", ("palestine", "palestinian", "gaza", "west bank", "ramallah", "hamas")),
    ("🇱🇧", ("lebanon", "lebanese", "beirut", "hezbollah")),
    ("🇸🇾", ("syria", "syrian", "damascus")),
    ("🇾🇪", ("yemen", "yemeni", "taiz", "houthi", "sanaa", "aden")),
    ("🇮🇷", ("iran", "iranian", "tehran", "khamenei", "bagheri", "okati")),
    ("🇮🇶", ("iraq", "iraqi", "baghdad")),
    ("🇸🇦", ("saudi", "riyadh")),
    ("🇦🇪", ("uae", "dubai", "abu dhabi", "emirates")),
    ("🇶🇦", ("qatar", "doha", "al jazeera")),
    ("🇴🇲", ("oman", "muscat")),
    ("🇰🇼", ("kuwait",)),
    ("🇧🇭", ("bahrain",)),
    ("🇯🇴", ("jordan", "amman")),
    ("🇨🇳", ("china", "chinese", "beijing", "xinhua", "cgtn")),
    ("🇹🇼", ("taiwan", "taipei")),
    ("🇭🇰", ("hong kong", "scmp")),
    ("🇯🇵", ("japan", "japanese", "tokyo", "nhk")),
    ("🇰🇵", ("north korea", "pyongyang", "kim jong")),
    ("🇰🇷", ("south korea", "korea", "seoul")),
    ("🇮🇳", ("india", "indian", "delhi", "mumbai", "modi")),
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

# HQ-location fallback: used only when the text names NO country.
# (Event location always wins: "Boeing opens Berlin plant" -> DE, not US.)
COMPANY_FLAGS = {
    "boeing": "🇺🇸", "palantir": "🇺🇸", "lockheed": "🇺🇸", "raytheon": "🇺🇸",
    "northrop": "🇺🇸", "spacex": "🇺🇸", "openai": "🇺🇸", "anduril": "🇺🇸",
    "airbus": "🇪🇺", "roscosmos": "🇷🇺", "cnec": "🇨🇳",
}

# Company-specialty topic icons: checked BEFORE the AI category.
# (Boeing makes planes -> jet, even in a Germany story.)
COMPANY_TOPIC = {
    "boeing": "✈️", "airbus": "✈️", "lockheed": "✈️", "raytheon": "✈️",
    "northrop": "✈️", "embraer": "✈️", "anduril": "✈️",
    "spacex": "🚀", "blue origin": "🚀", "nasa": "🚀", "roscosmos": "🚀",
    "palantir": "🤖", "openai": "🤖",
    "apple": "📱", "samsung": "📱",
    "tesla": "🚗", "toyota": "🚗", "byd": "🚗",
    "coinbase": "🪙", "binance": "🪙",
}

# AI-category icons (Gemini picks ONE category per story, same free call).
CATEGORY_EMOJI = {
    "conflict": "🪖", "aviation": "✈️", "naval": "🚢", "explosion": "💥",
    "space": "🚀", "ai": "🤖", "crypto": "🪙", "markets": "📈",
    "football": "⚽", "sport": "🏅", "film": "🎬", "gaming": "🎮",
    "health": "🦠", "politics": "🏛️", "diplomacy": "🤝", "justice": "⚖️",
    "business": "💼", "agriculture": "🌱", "other": "",
}
CATEGORIES = sorted(k for k in CATEGORY_EMOJI if k != "other") + ["other"]

# Outlet origin fallback (used only when the text names no country/company).
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

def _hit_pos(text, word):
    """Position of a word hit, or None. Short tokens match whole-word only."""
    w = word.strip()
    if len(w) <= 4:
        m = re.search(r"\b" + re.escape(w) + r"s?\b", text)
        return m.start() if m else None
    i = text.find(w)
    return i if i >= 0 else None

def _item_text(it):
    return f" {(it.get('title') or '')} {(it.get('summary') or '')} ".lower()

def story_flag(it):
    """Flag = WHERE the story happens (earliest location mention wins).
    Company HQ only when no location is named; outlet origin as last resort."""
    text = _item_text(it)
    best, best_pos = None, None
    for flag, words in FLAG_RULES:
        for w in words:
            p = _hit_pos(text, w)
            if p is not None and (best_pos is None or p < best_pos):
                best, best_pos = flag, p
    if best:
        return best
    for company, flag in COMPANY_FLAGS.items():
        if _hit_pos(text, company) is not None:
            return flag
    outlet = (it.get("outlet") or it.get("source") or "")
    if outlet in OUTLET_FLAGS:
        return OUTLET_FLAGS[outlet]
    return PILLAR_EMOJI.get(it.get("pillar"), "📰")

def story_topic(it, category=None):
    """Topic icon: known-company specialty first, then the AI category."""
    text = _item_text(it)
    for company, emoji in COMPANY_TOPIC.items():
        if _hit_pos(text, company) is not None:
            return emoji
    if category in CATEGORY_EMOJI:
        return CATEGORY_EMOJI[category]
    return ""

def story_emoji(it, category=None):
    """Full story icon: flag + topic (e.g. 🇩🇪✈️). Topic collapses when it
    repeats the flag (no 🎬🎬). Flag alone if no topic."""
    flag = story_flag(it)
    topic = story_topic(it, category)
    if topic and topic != flag:
        return flag + topic
    return flag

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

def _story_block(num, it, summaries, categories=None):
    s = summaries.get(it["link"], it["title"])
    cat = (categories or {}).get(it["link"])
    corr = " ✅ 2 sources" if it.get("_corroborated") else ""
    src = f" — {_outlet(it)}" if not it.get("via_channel") else f" — via @{it['source']}"
    return (f"{num}. {story_emoji(it, cat)} *{esc(_clean(it['title']))}*{esc(corr)}\n"
            f"   {esc(_clean(cut_words(s, 200)))}{esc(src)} [link]({it['link']})\n")

def pick_hero(items):
    """Prefer images from wires with reliable hotlinking, else first available."""
    trusted = ("BBC", "CNA", "SCMP", "RT", "NHK", "CoinDesk", "Cointelegraph",
               "Telegraph", "AlJazeera", "africaintel", "BellumActaNews")
    for it in items:
        if it.get("image") and str(it.get("source", "")).startswith(trusted):
            return it["image"]
    return next((it.get("image", "") for it in items if it.get("image")), "")

def build_digest_chunks(slot_label, date_label, items, summaries, categories=None,
                        digest_title="NEWSROOM", header_emoji="🌍", pillars=None,
                        footer="_#digest • Full stories via links • via NewsRoom_"):
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
            body_blocks.append(_story_block(n, it, summaries, categories))
            n += 1
    for p in order:
        rest = [x for x in grouped.get(p, []) if x not in top]
        if not rest:
            continue
        body_blocks.append(f"{PILLAR_EMOJI.get(p, '📰')} *{PILLAR_TITLE.get(p, p.upper())}*\n")
        for it in rest:
            body_blocks.append(_story_block(n, it, summaries, categories))
            n += 1
    body_blocks.append(footer)

    # photo caption: header + top-1 story only (caption cap = 1024)
    first = top[0] if top else items[0]
    caption = (header + f"\n🔥 *TOP STORY*\n" +
               _story_block(1, first, summaries, categories) +
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

def build_breaking(items, summaries, categories=None):
    lines = ["🚨 *BREAKING*\n"]
    n = 1
    for it in items:
        s = summaries.get(it["link"], it["title"])
        cat = (categories or {}).get(it["link"])
        src = f" — {_outlet(it)}" if not it.get("via_channel") else f" — via @{it['source']}"
        lines.append(f"{story_emoji(it, cat)} *{esc(_clean(it['title']))}*\n"
                     f"   {esc(_clean(cut_words(s, 200)))}{esc(src)} [link]({it['link']})\n")
        n += 1
    lines.append("_Developing story • verify via links • via NewsRoom_")
    text = "\n".join(lines)
    return [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]

def _join_button(join_url):
    if not join_url:
        return None
    return {"inline_keyboard": [[{"text": "📣 Join the Newsroom", "url": join_url}]]}

def send_digest(channel, token, caption, chunks, hero_image="", dry_run=False, join_url=None):
    if dry_run:
        print("── DRY RUN (no post) ──")
        print(f"[photo: {hero_image or 'none'}]\nCAPTION:\n{caption}\n")
        for i, c in enumerate(chunks, 1):
            print(f"--- MESSAGE {i}/{len(chunks)} ---\n{c}\n")
        if join_url:
            print(f"[join button: {join_url} on last message]")
        return {"ok": True, "dry_run": True, "messages": 1 + len(chunks)}
    sent = []
    if hero_image:
        try:
            sent.append(_api(token, "sendPhoto", {
                "chat_id": channel, "photo": hero_image,
                "caption": caption, "parse_mode": "Markdown"}))
        except Exception as ex:
            print(f"sendPhoto failed ({ex}), posting text only")
    for i, c in enumerate(chunks):
        payload = {"chat_id": channel, "text": c,
                   "parse_mode": "Markdown", "disable_web_page_preview": False}
        if join_url and i == len(chunks) - 1:
            payload["reply_markup"] = _join_button(join_url)
        sent.append(_api(token, "sendMessage", payload))
    return {"ok": True, "messages": len(sent)}

def send_breaking(channel, token, chunks, hero_image="", dry_run=False, join_url=None):
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
    for i, c in enumerate(chunks):
        payload = {"chat_id": channel, "text": c,
                   "parse_mode": "Markdown", "disable_web_page_preview": False}
        if join_url and i == len(chunks) - 1:
            payload["reply_markup"] = _join_button(join_url)
        _api(token, "sendMessage", payload)
    return {"ok": True}
