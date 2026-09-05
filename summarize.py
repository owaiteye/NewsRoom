"""Polish summaries with Gemini Free; ALWAYS fall back to offline extractive."""
import os
import re
import requests

def _extractive(title, summary, max_words=28):
    text = re.sub(r"<[^>]+>", " ", summary or "").strip()
    text = re.sub(r"\s+", " ", text)
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

def _gemini_polish(title, summary):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no-key")
    prompt = (
        "Summarize this news in ONE line, under 25 words, plain, no hype, no emoji. "
        f"Title: {title}\nSnippet: {(summary or '')[:600]}"
    )
    last_err = "no-model-tried"
    for model in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')[:220]
        except Exception as ex:
            last_err = f"{model}: {ex}"
    raise RuntimeError(last_err)

def summarize_item(title, summary):
    try:
        s = _gemini_polish(title, summary)
        return s[:220] if len(s) > 220 else s
    except Exception:
        return _extractive(title, summary)  # quota-safe: bot never dies
