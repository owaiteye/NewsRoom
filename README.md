# NewsRoom — $0 serverless Telegram news digest bot

> **Live demo:** join [@generalintel on Telegram](https://t.me/generalintel)
> to see it in action — digests post daily, breaking news as it happens.

Turns RSS feeds, Google News, and Telegram channels you follow into **short,
readable digests** posted to your Telegram channel — automatically, 4x a day,
with breaking-news alerts in between. No server, no paid APIs, no babysitting.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## What it does

- 📥 **Collects** from three tiers: direct RSS (~25 outlets), Google News RSS
  queries (covers regional press with unstable/no RSS), and Telegram channels
  you already follow (the fastest source — optional).
- 🧹 **Dedupes** by URL hash + fuzzy title match (7-day rolling state, auto-pruned).
- 🏆 **Ranks** by recency, source trust, and cross-source corroboration.
- ✨ **Summarizes** each story to one line with a free Gemini key — with an
  **offline fallback**, so the bot never dies if the key/quota fails.
- 📰 **Posts two digests per slot** to your channel:
  - 🌍 `NEWSROOM` — your region + world/geopolitics
  - 💻 `NEWSROOM+` — tech, crypto/finance, entertainment/sport
- 🚨 **Breaking gate**: posts instantly only if 2+ independent sources report
  the same event within 90 min (or a trusted wire says BREAKING) — max 2/run.
- 🏳️ Stories carry **country-flag icons** (deterministic keyword map) and
  `via @source` attribution for Telegram forwards.

## How it works (free forever)

```
GitHub Actions (cron, ~540/2000 free min/month)
  -> collector.py (RSS + Google News, parallel, 20s timeouts)
  -> listener.py  (Telegram channels, read-only user session, optional)
  -> dedupe.py    (state.json, 7-day window, committed back to repo)
  -> rank.py      (score + corroboration + breaking picks)
  -> summarize.py (Gemini free tier -> offline extractive fallback)
  -> publish.py   (hero photo + chunked Markdown messages via Bot API)
```

## Setup (about 30 minutes, no server knowledge needed)

### 1. Telegram bot
1. Chat with **BotFather** → `/newbot` → save the token.
2. Add the bot as **Administrator** of your channel (only needs *Post Messages*).

### 2. Free Gemini key (optional but recommended)
1. Go to **Google AI Studio** → create an API key (free, no card).
2. Without it the bot still works — summaries fall back to extractive mode.

### 3. GitHub repo + secrets
1. Fork/clone this repo (default branch: `master`).
2. Repo → **Settings → Secrets → Actions** → add:
   - `TELEGRAM_BOT_TOKEN` — from step 1
   - `TELEGRAM_CHANNEL_ID` — e.g. `@yourchannel`
   - `GEMINI_API_KEY` — from step 2 (optional)
3. **Actions** tab → enable workflows. Scheduled runs post live;
   manual runs default to a dry-run preview in the logs.

### 4. Telegram channel listener (optional, fastest news)
Bots can't read channels they aren't admin of, so this uses a **read-only
login as yourself**:
1. **my.telegram.org** → log in → **API development tools** → create app →
   copy `API_ID` + `API_HASH`.
2. Locally: `pip install telethon && python make_session.py` → enter phone,
   the login code Telegram sends you, and 2FA password if you have one.
3. Add three more secrets: `API_ID`, `API_HASH`, `TELEGRAM_SESSION_STRING`.
4. Revoke anytime: Telegram → Settings → Devices → terminate the session.

### 5. Make it yours
All curation lives in **`config/sources.yaml`** — feeds, Google News queries,
Telegram channels, trust levels, breaking keywords. No code changes needed.
Posting times are cron expressions in `.github/workflows/digest.yml`
(default 06:00 / 12:00 / 18:00 / 00:00 East Africa Time).

## Local preview

```bash
pip install -r requirements.txt
cp .env.example .env   # fill tokens
python run_local.py            # safe dry-run preview
python run_local.py --live     # actually posts
python main.py --mode digest --dry-run
python main.py --mode breaking-only --dry-run
```

## Costs & limits

| Piece | Cost |
|---|---|
| GitHub Actions | $0 (uses ~540 of 2000 free min/mo) |
| Gemini summaries | $0 (~7k of 1M free tokens/day) |
| Telegram Bot API | $0, no limits that matter here |
| Server | none — there isn't one |

## Project layout

```
config/sources.yaml      all feeds, queries, channels, trust, keywords
collector.py             RSS + Google News fetching (threaded)
listener.py              Telegram channel reader (V2, Telethon)
make_session.py          interactive helper to create the TG session string
dedupe.py / rank.py      dedupe, scoring, corroboration, breaking picks
summarize.py             Gemini polish + offline fallback
publish.py               digest building, flags, Telegram sending
main.py / run_local.py   entry points (Actions / phone-or-PC manual run)
.github/workflows/       digest.yml (4x/day) + breaking.yml (hourly gate)
```

## Notes & fair use

- Forwarded Telegram items keep `via @channel` attribution with a link back.
- Summaries are one-line paraphrases, not full-text copies.
- Post at reasonable volumes; respect outlets' terms and your country's laws.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, run your own channel with it.

## Maintenance status

This is a personal project published as-is for anyone to use. The maintainer
is busy running a news channel, so **issues and pull requests may not be
reviewed — please fork freely** instead of waiting on upstream. The automated
test suite (`python tests/test_flags.py`, also run in CI) guards the icon
rules; run it before any change to flag/topic logic.
