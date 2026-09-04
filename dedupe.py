"""Dedupe by URL hash + fuzzy title match. Offline, no AI needed."""
import hashlib
import json
import os
import re
import time

try:
    from rapidfuzz.fuzz import token_set_ratio
    def _sim(a, b):
        return token_set_ratio(a, b) / 100.0
except Exception:
    import difflib
    def _sim(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()

STATE_FILE = os.environ.get("STATE_FILE", "state.json")
RETENTION_DAYS = 7
SIM_THRESHOLD = 0.82

def _norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _url_id(link):
    return hashlib.sha256((link or "").strip().lower().encode()).hexdigest()[:16]

def load_state():
    try:
        with open(STATE_FILE) as f:
            st = json.load(f)
            if isinstance(st, dict) and "seen" in st:
                return st
    except Exception:
        pass
    return {"seen": []}  # list of {id, title_norm, ts}

def save_state(state):
    cutoff = time.time() - RETENTION_DAYS * 86400
    state["seen"] = [s for s in state.get("seen", []) if s.get("ts", 0) > cutoff][-2000:]
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def dedupe(items, state):
    seen_ids = {s["id"] for s in state.get("seen", [])}
    seen_titles = [(s.get("title_norm", ""), s.get("ts", 0)) for s in state.get("seen", [])][-500:]
    fresh = []
    for it in items:
        uid = _url_id(it["link"])
        if uid in seen_ids:
            continue
        nt = _norm_title(it["title"])
        dup = False
        for st_title, _ in seen_titles[-200:]:
            if st_title and _sim(nt, st_title) >= SIM_THRESHOLD:
                dup = True
                break
        if dup:
            continue
        # in-batch check against already accepted
        for acc in fresh:
            if _sim(nt, _norm_title(acc["title"])) >= SIM_THRESHOLD:
                dup = True
                break
        if dup:
            continue
        fresh.append(it)
    return fresh

def mark_seen(items, state):
    for it in items:
        state.setdefault("seen", []).append({
            "id": _url_id(it["link"]),
            "title_norm": _norm_title(it["title"]),
            "ts": time.time(),
        })
