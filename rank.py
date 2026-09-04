"""Rule-based scoring. No AI required. Corroboration = breaking signal."""
import re
import time
from collections import defaultdict

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

def score_items(items):
    # group near-identical titles to detect corroboration (2+ sources, same event)
    groups = defaultdict(list)
    for it in items:
        key = " ".join(sorted(set(_norm(it["title"]).split()))[:8])
        groups[key].append(it)
    # simpler: count shared rare words — use first 6 significant words as bucket
    for it in items:
        age_h = max(0, (time.time() - it.get("ts", time.time())) / 3600)
        recency = 3 if age_h <= 3 else (2 if age_h <= 6 else (1 if age_h <= 12 else 0))
        s = recency + min(3, it.get("trust", 3) - 1)
        text = _norm(it["title"] + " " + it.get("summary", ""))
        for kw_list in PILLAR_KEYWORDS.values():
            if any(k in text for k in kw_list):
                s += 1
                break
        if any(k in text for k in ["breaking", "urgent", "coup", "explosion", "earthquake"]):
            s += 2
        it["_score"] = s
    # corroboration bonus: same story from 2+ distinct sources
    by_words = defaultdict(set)
    for it in items:
        words = tuple(sorted(set(w for w in _norm(it["title"]).split() if len(w) > 4))[:5])
        by_words[words].add(it["source"])
    for it in items:
        words = tuple(sorted(set(w for w in _norm(it["title"]).split() if len(w) > 4))[:5])
        if len(by_words.get(words, set())) >= 2:
            it["_score"] += 3
            it["_corroborated"] = True
    items.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return items

def pick_digest(items, limit=12):
    return items[:limit]

def pick_breaking(items, sources_cfg, max_per_run=3):
    wl = set(sources_cfg.get("breaking_whitelist", []))
    kws = [k.lower() for k in sources_cfg.get("breaking_keywords", [])]
    cands = []
    for it in items:
        text = (it["title"] + " " + it.get("summary", "")).lower()
        kw_hit = any(k in text for k in kws)
        wl_hit = it["source"] in wl
        if it.get("_corroborated") or (kw_hit and wl_hit) or (kw_hit and it.get("trust", 0) >= 4):
            # Uganda stories get priority
            if it.get("pillar") == "uganda":
                it["_score"] += 1
            cands.append(it)
    cands.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return cands[:max_per_run]
