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

DIGEST_GROUPS = [
    {"title": "NEWSROOM", "emoji": "🌍", "pillars": ["uganda", "geopolitics"], "limit": 8},
    {"title": "NEWSROOM+", "emoji": "💻", "pillars": ["tech", "crypto", "entertainment"], "limit": 8},
]

EAT = datetime.timezone(datetime.timedelta(hours=3))
SLOTS = {3: "06:00 EAT Morning Brief", 9: "12:00 EAT Midday",
         15: "18:00 EAT Evening", 21: "00:00 EAT Night Wrap"}

def slot_label(now_utc=None):
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    h = now_utc.hour
    best = min(SLOTS, key=lambda k: abs(k - h))
    return SLOTS[best]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="digest", choices=["digest", "breaking-only"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open("config/sources.yaml") as f:
        cfg = yaml.safe_load(f)

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
        picks = pick_breaking(scored, cfg)
        if not picks:
            print("breaking: no candidates, nothing to post.")
            return
        summaries = {it["link"]: summarize_item(it["title"], it.get("summary", ""), it.get("outlet", it.get("source", ""))) for it in picks}
        chunks = build_breaking(picks, summaries)
        hero = next((it.get("image", "") for it in picks if it.get("image")), "")
        if not args.dry_run:
            mark_seen(picks, state); save_state(state)
        send_breaking(channel, token, chunks, hero_image=hero, dry_run=args.dry_run)
        print(f"breaking: posted {len(picks)}")
        return

    picks = pick_digest(scored, limit=16)
    if not picks:
        print("digest: nothing fresh, nothing to post.")
        return
    summaries = {it["link"]: summarize_item(it["title"], it.get("summary", ""), it.get("outlet", it.get("source", ""))) for it in picks}
    total = 0
    for g in DIGEST_GROUPS:
        g_items = [it for it in picks if it.get("pillar") in g["pillars"]][:g["limit"]]
        if not g_items:
            print(f"digest {g['title']}: empty, skipped")
            continue
        caption, chunks = build_digest_chunks(
            slot_label(), date_label, g_items, summaries,
            digest_title=g["title"], header_emoji=g["emoji"], pillars=g["pillars"])
        hero = pick_hero(g_items)
        if not args.dry_run:
            mark_seen(g_items, state)
        send_digest(channel, token, caption, chunks, hero_image=hero, dry_run=args.dry_run)
        total += len(g_items)
        print(f"digest {g['title']}: posted {len(g_items)} stories in {len(chunks)} text messages")
    if not args.dry_run:
        save_state(state)

if __name__ == "__main__":
    main()
