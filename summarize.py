"""Polish summaries with Gemini Free; ALWAYS fall back to offline extractive."""
import os
import re
import requests

def _extractive(title, summary, max_words=28, outlet=""):
    import html as _html
    text = re.sub(r"<[^>]+>", " ", summary or "").strip()
    text = _html.unescape(text).replace("\xa0", " ").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if outlet:
        # Google News appends " - Outlet" / " Outlet" tails; drop them
        text = re.sub(r"\s*[–—-]\s*" + re.escape(outlet) + r"\s*$", "", text).strip()
        text = re.sub(r"\s+" + re.escape(outlet) + r"\s*$", "", text).strip()
    # drop trailing " - Something" tail that Google News appends
    text = re.split(r"\s+[-–—]\s+[A-Z][\w ]{2,40}$", text)[0].strip()
    if not text:
        return title.strip()
    # first ~2 sentences
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = " ".join(parts[:2]).strip()
    words = out.split()
    if len(words) > max_words:
        out = " ".join(words[:max_words]) + "…"
    return out or title.strip()

GEMINI_MODELS = (
    "gemini-3.5-flash-lite",  # cheapest, biggest free quota — primary
    "gemini-3.6-flash",       # fallback if lite unavailable
)

CATEGORY_CHOICES = ("conflict, aviation, naval, explosion, space, ai, crypto, "
                    "markets, football, sport, film, gaming, health, politics, "
                    "diplomacy, justice, business, agriculture, other")

def _gemini_polish(title, summary):
    """Returns (category|None, one-line summary). Same single free call."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no-key")
    prompt = (
        "You are a news classifier. Reply in EXACTLY two lines:\n"
        f"CATEGORY: <one of: {CATEGORY_CHOICES}>\n"
        "SUMMARY: <one line, under 25 words, plain, no hype, no emoji>\n"
        f"Title: {title}\nSnippet: {(summary or '')[:600]}"
    )
    last_err = "no-model-tried"
    for model in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
            r.raise_for_status()
            data = r.json()
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            cat, text = None, raw
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            for ln in lines:
                low = ln.lower()
                if low.startswith("category:"):
                    c = low.split(":", 1)[1].strip().strip('".,*')
                    from publish import CATEGORY_EMOJI
                    cat = c if c in CATEGORY_EMOJI else None
                elif low.startswith("summary:"):
                    text = ln.split(":", 1)[1].strip().strip('"')
            return cat, text[:220]
        except Exception as ex:
            last_err = f"{model}: {ex}"
    raise RuntimeError(last_err)

def summarize_item(title, summary, outlet=""):
    """Returns (category|None, one-line summary). Never raises: offline fallback."""
    try:
        return _gemini_polish(title, summary)
    except Exception:
        return None, _extractive(title, summary, outlet=outlet)  # quota-safe: bot never dies
