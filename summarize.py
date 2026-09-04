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

def _gemini_polish(title, summary):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no-key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
    prompt = (
        "Summarize this news in ONE line, under 25 words, plain, no hype, no emoji. "
        f"Title: {title}\nSnippet: {(summary or '')[:600]}"
    )
    r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
    r.raise_for_status()
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
    except Exception as ex:
        raise RuntimeError(f"bad-response: {ex}")

def summarize_item(title, summary):
    try:
        s = _gemini_polish(title, summary)
        return s[:220] if len(s) > 220 else s
    except Exception:
        return _extractive(title, summary)  # quota-safe: bot never dies
