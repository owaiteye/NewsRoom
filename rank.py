"""Rule-based scoring. No AI required. Corroboration = breaking signal."""
import re
import time

from publish import _word_hit

PILLAR_KEYWORDS = {
    "uganda": ["uganda", "kampala", "museveni", "parliament", "updf", "shilling", "entebbe"],
    "geopolitics": ["gaza", "ukraine", "coup", "summit", "sanctions", "ceasefire", "election"],
    "tech": ["ai", "chip", "smartphone", "laptop", "gpu", "apple", "android"],
    "crypto": ["bitcoin", "eth", "crypto", "binance", "etf", "stablecoin"],
    "entertainment": ["premiere", "trailer", "box office", "premier league", "transfer"],
}

def _norm(t):
    t = (t or "").lower()
    return re.sub(r"[^a-z0-9\s]", " ", t)

UGANDA_WORDS = ("uganda", "kampala", "museveni", "updf", "entebbe", "omukama",
                "parliament", "shilling", "ntv uganda", "new vision", "daily monitor")
ENT_WORDS = ("league", "cup", "match", "victory", "win ", "wins", "beats", "series lead",
             "playoff", "transfer", "derby", "coach", "jersey", "stage ", "trailer",
             "box office", "premiere", "season", "netflix", "episode", "rugby", "cricket")

def reclassify(items):
    """Fix pillar for items from generic feeds (CNA, BBC Top, GNews region queries)
    AND Telegram forwards (a geopolitics channel often posts sport/entertainment)."""
    for it in items:
        t = _norm(it["title"] + " " + it.get("summary", ""))
        if any(_word_hit(t, w) for w in ENT_WORDS):
            it["pillar"] = "entertainment"
            continue
        if it.get("via_channel"):
            continue  # keep curated channel pillar otherwise
        if it.get("pillar") == "uganda" and not any(_word_hit(t, w) for w in UGANDA_WORDS):
            # region-query item with no Uganda hook (e.g. SA rugby) -> world
            it["pillar"] = "geopolitics"

def _title_sim(a, b):
    try:
        from rapidfuzz.fuzz import token_set_ratio
        return token_set_ratio(a, b) / 100.0
    except Exception:
        import difflib
        return difflib.SequenceMatcher(None, a, b).ratio()

def score_items(items):
    for it in items:
        age_h = max(0, (time.time() - it.get("ts", time.time())) / 3600)
        recency = 3 if age_h <= 3 else (2 if age_h <= 6 else (1 if age_h <= 12 else 0))
        s = recency + min(3, it.get("trust", 3) - 1)
        text = _norm(it["title"] + " " + it.get("summary", ""))
        for kw_list in PILLAR_KEYWORDS.values():
            if any(_word_hit(text, k) for k in kw_list):
                s += 1
                break
        if any(_word_hit(text, k) for k in ["breaking", "urgent", "coup", "explosion", "earthquake"]):
            s += 2
        it["_score"] = s
    # corroboration: similar title from a DIFFERENT source (pairwise, top-80 only for speed).
    # Requires decent-length titles to avoid short-title collisions.
    cands = sorted(items, key=lambda x: x.get("_score", 0), reverse=True)[:80]
    norms = [_norm(c["title"]) for c in cands]
    for i, it in enumerate(cands):
        if len(norms[i].split()) < 5:
            continue
        for j, other in enumerate(cands):
            if i == j or other["source"] == it["source"]:
                continue
            if len(norms[j].split()) < 5:
                continue
            if _title_sim(norms[i], norms[j]) >= 0.55:
                it["_score"] += 3
                it["_corroborated"] = True
                break
    items.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return items

def pick_digest(items, limit=14):
    return items[:limit]

# Evergreen content (listicles, rankings) is never breaking news,
# no matter how many outlets publish lookalikes the same day.
EVERGREEN_RES = (
    re.compile(r"\b\d+\s+(greatest|best|worst|top|most|funniest)\b", re.I),
    re.compile(r"\bof all time\b", re.I),
    re.compile(r"\branked\b", re.I),
)

def _is_evergreen(title):
    return any(rx.search(title or "") for rx in EVERGREEN_RES)

def pick_breaking(items, sources_cfg, max_per_run=2):
    wl = set(sources_cfg.get("breaking_whitelist", []))
    kws = [k.lower() for k in sources_cfg.get("breaking_keywords", [])]
    cands = []
    for it in items:
        if it.get("pillar") == "entertainment":
            continue  # lifestyle/sport/showbiz never breaks, even corroborated
        if _is_evergreen(it.get("title")):
            continue  # listicles/rankings are not news events
        title = (it["title"] or "").lower()
        kw_hit = any(k in title for k in kws)  # title only — summaries cause false flags
        if it.get("_corroborated"):
            pass  # 2+ independent sources, any pillar
        elif it["source"] in wl and kw_hit and it.get("pillar") != "entertainment":
            pass  # trusted wire + explicit breaking word, no lifestyle stories
        else:
            continue
        if it.get("pillar") == "uganda":
            it["_score"] += 1
        cands.append(it)
    cands.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return cands[:max_per_run]
