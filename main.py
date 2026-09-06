"""Entry point: python main.py --mode digest|breaking-only [--dry-run]"""
import argparse
import datetime
import os
import yaml

from collector import collect
from dedupe import load_state, save_state, dedupe, mark_seen
from rank import score_items, pick_digest, pick_breaking, reclassify
from summarize import summarize_item
from publish import build_digest_chunks, build_breaking, send_digest, send_breaking, pick_hero

EAT = datetime.timezone(datetime.timedelta(hours=3))
SLOTS = {3: "Morning Wrap", 9: "Afternoon Wrap",
         15: "Evening Wrap", 21: "Night Wrap"}

DEFAULT_BRANDING = {
    "digest_a_title": "NEWSROOM", "digest_a_emoji": "🌍",
    "digest_b_title": "NEWSROOM+", "digest_b_emoji": "⚡",
    "demo_link": "https://t.me/generalintel",
    "footer": "📣 [Join the Newsroom](https://t.me/generalintel) • #digest",
}

def slot_label(now_utc=None):
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    h = now_utc.hour
    best = min(SLOTS, key=lambda k: abs(k - h))
    return SLOTS[best]

def summarize_all(picks):
    """Returns (summaries, categories) dicts keyed by link. Never raises."""
    summaries, categories = {}, {}
    for it in picks:
        try:
            cat, text = summarize_item(
                it["title"], it.get("summary", ""),
                it.get("outlet", it.get("source", "")))
        except Exception as ex:
            print(f"summarize fallback ({ex})")
            cat, text = None, (it.get("summary") or it["title"])[:200]
        summaries[it["link"]] = text
        if cat:
            categories[it["link"]] = cat
    return summaries, categories

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="digest", choices=["digest", "breaking-only"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open("config/sources.yaml") as f:
        cfg = yaml.safe_load(f)
    brand = {**DEFAULT_BRANDING, **cfg.get("branding", {})}
    groups = [
        {"title": brand["digest_a_title"], "emoji": brand["digest_a_emoji"],
         "pillars": ["uganda", "geopolitics"], "limit": 8},
        {"title": brand["digest_b_title"], "emoji": brand["digest_b_emoji"],
         "pillars": ["tech", "crypto", "entertainment"], "limit": 8},
    ]

    items, errors = collect(cfg)
    if errors:
        print(f"collector: {len(items)} items, {len(errors)} feed errors (normal):")
        for e in errors[:8]:
            print(f"  - {e}")

    # V2: optionally merge Telegram channel posts (skips silently in V1)
    try:
        from listener import fetch_channel_posts
        if os.environ.get("TELEGRAM_SESSION_STRING"):
            items += fetch_channel_posts()
    except Exception as ex:
        print(f"listener skipped: {ex}")

    state = load_state()
    fresh = dedupe(items, state)
    print(f"dedupe: {len(items)} -> {len(fresh)} fresh")
    reclassify(fresh)
    scored = score_items(fresh)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "@generalintel")
    now_eat = datetime.datetime.now(EAT)
    date_label = now_eat.strftime("%d %b %Y")

    if args.mode == "breaking-only":
        # stage 1: cheap rules (no AI) -> summarize survivors only -> stage 2: AI category gate
        candidates = pick_breaking(scored, cfg, max_per_run=6, apply_category=False)
        if not candidates:
            print("breaking: no candidates, nothing to post.")
            return
        summaries, categories = summarize_all(candidates)
        for it in candidates:
            it["_cat"] = categories.get(it["link"])
        picks = pick_breaking(candidates, cfg)
        if not picks:
            print("breaking: category gate dropped all candidates, nothing to post.")
            return
        chunks = build_breaking(picks, summaries, categories)
        hero = next((it.get("image", "") for it in picks if it.get("image")), "")
        send_breaking(channel, token, chunks, hero_image=hero,
                      dry_run=args.dry_run, join_url=brand["demo_link"])
        if not args.dry_run:
            # marked AFTER a successful send: a failed run retries next time
            mark_seen(picks, state); save_state(state)
        print(f"breaking: posted {len(picks)}")
        return

    picks = pick_digest(scored, limit=16)
    if not picks:
        print("digest: nothing fresh, nothing to post.")
        return
    summaries, categories = summarize_all(picks)
    for g in groups:
        g_items = [it for it in picks if it.get("pillar") in g["pillars"]][:g["limit"]]
        if not g_items:
            print(f"digest {g['title']}: empty, skipped")
            continue
        caption, chunks = build_digest_chunks(
            slot_label(), date_label, g_items, summaries, categories,
            digest_title=g["title"], header_emoji=g["emoji"],
            pillars=g["pillars"], footer=brand["footer"])
        hero = pick_hero(g_items)
        send_digest(channel, token, caption, chunks, hero_image=hero,
                    dry_run=args.dry_run, join_url=brand["demo_link"])
        if not args.dry_run:
            mark_seen(g_items, state)
        print(f"digest {g['title']}: posted {len(g_items)} stories in {len(chunks)} text messages")
    if not args.dry_run:
        save_state(state)

if __name__ == "__main__":
    main()
