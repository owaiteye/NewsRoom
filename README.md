# NewsRoom — @generalintel digest bot ($0, zero-server)

4x daily digest (06:00 / 12:00 / 18:00 / 00:00 EAT) + hourly breaking gate.
RSS + Google News now; Telegram channel listener in V2.

## 1. Setup (15 min, novice)

1. Telegram → `BotFather` → `/newbot` → copy token. Add bot as Admin to `@generalintel` (Post Messages only).
2. Google AI Studio → create `GEMINI_API_KEY` (free, no card).
3. GitHub → this repo → `Settings → Secrets → Actions` → add:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID` (`@generalintel`), `GEMINI_API_KEY`.
   V2 only: `API_ID`, `API_HASH`, `TELEGRAM_SESSION_STRING`.
4. `Actions` tab → enable workflows. `digest.yml` posts live on schedule; manual run defaults to dry-run preview.

## 2. Local / phone preview

```bash
pip install -r requirements.txt
cp .env.example .env   # fill tokens
python run_local.py            # safe: dry-run preview
python run_local.py --live     # actually posts
python main.py --mode digest --dry-run
python main.py --mode breaking-only --dry-run
```

## 3. How it works

`collector (RSS+GNews)` → `dedupe (url hash + fuzzy title, 7-day state.json)` →
`rank (recency+trust+corroboration)` → `summarize (Gemini → offline fallback)` →
`publish (1 hero photo + digest text + link previews)`.

Breaking posts only if: 2+ sources in 90 min, or whitelist + keyword + unseen. Max 3/run.

## 4. Costs / limits

GitHub Actions ~540/2000 free min/mo. Gemini ~7k/1M tokens/day. No server, `state.json` auto-prunes to 7 days.

## 5. If something breaks

* No post but logs show "nothing fresh" → normal (dedupe working).
* `sendPhoto failed` → auto-falls back to text. Normal.
* 401 from Telegram → token revoked/wrong: `BotFather → /revoke`, update secret.
* Gemini 429 → offline summaries used automatically. Nothing to do.
