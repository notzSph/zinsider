# zInsider

![Version](https://img.shields.io/badge/Version-2.0-blue.svg)
![Build](https://img.shields.io/badge/Build-passing-brightgreen.svg)
![License](https://img.shields.io/badge/License-Proprietary-red.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)
![Database](https://img.shields.io/badge/Database-SQLite-003B57.svg)
![Container](https://img.shields.io/badge/Container-Docker-2496ED.svg)
![Output](https://img.shields.io/badge/Output-Discord-5865F2.svg)

zInsider is a private market-structure scanner for FX and futures monitoring.

Version 2.0+ separates data collection from publishing:

- FX data comes from TradingView Pine alerts into `/webhooks/tradingview`.
- Futures data is pulled with `yfinance`.
- Computed bars and signals are stored in SQLite.
- Discord output is routed to digest/model threads instead of one noisy wall of text.

The system is designed for private workflow automation, market-structure scanning, setup detection, and clean Discord delivery.

---

## Version

```text
2.0
```

---

## Status

```text
Build: Passing
License: Proprietary
Runtime: Python
Database: SQLite
Output: Discord bot
```

---

## Features

- TradingView webhook ingestion for FX OHLC data.
- Futures data collection through `yfinance`.
- SQLite persistence for bars, computed state, and signals.
- Inside day detection.
- Inside week detection.
- Rounded retest tracking.
- Zebra model output.
- Futures rollover alerts.
- Daily digest stream.
- Discord thread routing by model/stream.
- Discord bot delivery and optional presence.
- Dockerized deployment.
- CLI commands for serving, scanning, initializing the database, and printing stats.

---

## Repository Structure

```text
.
├── Dockerfile
├── LICENSE
├── README.md
├── app
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py
│   ├── modules
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── assets.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── inside.py
│   │   ├── market.py
│   │   ├── render.py
│   │   ├── retest.py
│   │   ├── signals.py
│   │   ├── state.py
│   │   ├── webhooks.py
│   │   └── zebra.py
│   ├── presence.py
│   ├── scheduler.py
│   └── server.py
├── docker-compose.yml
└── requirements.txt
```

Note: `__pycache__/` directories and `.pyc` files are runtime artifacts and should not be committed.

---

## Project Layout

### `app/`

Main Python package and application entrypoints.

| File | Purpose |
| --- | --- |
| `__main__.py` | Module entrypoint for `python3 -m app`. |
| `main.py` | CLI command routing and application control. |
| `presence.py` | Optional Discord bot presence handling. |
| `scheduler.py` | Scheduled scan / task orchestration. |
| `server.py` | Webhook server for TradingView ingestion. |

### `app/modules/`

Core scanning, storage, signal, and publishing modules.

| File | Purpose |
| --- | --- |
| `analyzer.py` | Market-structure analysis orchestration. |
| `assets.py` | Asset definitions, aliases, and symbol handling. |
| `config.py` | Environment and runtime configuration. |
| `db.py` | SQLite database access and persistence. |
| `inside.py` | Inside day / inside week logic. |
| `market.py` | Market data fetching and normalization. |
| `render.py` | Discord message rendering. |
| `retest.py` | Rounded retest detection. |
| `signals.py` | Signal construction and routing. |
| `state.py` | Runtime state management. |
| `webhooks.py` | Discord bot message delivery. |
| `zebra.py` | Zebra model logic. |

---

## Discord Streams

Configure the Discord bot token and output thread IDs:

```env
DISCORD_BOT_TOKEN=...
DISCORD_DAILY_DIGEST_THREAD_ID=
DISCORD_WEEKLY_DIGEST_THREAD_ID=
DISCORD_ID_THREAD_ID=
DISCORD_IW_THREAD_ID=
DISCORD_DAILY_RR_PLUS_THREAD_ID=
DISCORD_DAILY_RR_MINUS_THREAD_ID=
DISCORD_WEEKLY_RR_PLUS_THREAD_ID=
DISCORD_WEEKLY_RR_MINUS_THREAD_ID=
DISCORD_DAILY_ZEBRA_THREAD_ID=
DISCORD_WEEKLY_ZEBRA_THREAD_ID=
DISCORD_ROLLOVER_THREAD_ID=
```

Streams:

| Variable | Purpose |
| --- | --- |
| `DISCORD_DAILY_DIGEST_THREAD_ID` | Compact weekday summary. |
| `DISCORD_WEEKLY_DIGEST_THREAD_ID` | Friday weekly summary. |
| `DISCORD_ID_THREAD_ID` | Inside day logs. |
| `DISCORD_IW_THREAD_ID` | Inside week logs. |
| `DISCORD_DAILY_RR_PLUS_THREAD_ID` | Daily bullish rounded retest logs. |
| `DISCORD_DAILY_RR_MINUS_THREAD_ID` | Daily bearish rounded retest logs. |
| `DISCORD_WEEKLY_RR_PLUS_THREAD_ID` | Friday bullish weekly rounded retest logs. |
| `DISCORD_WEEKLY_RR_MINUS_THREAD_ID` | Friday bearish weekly rounded retest logs. |
| `DISCORD_DAILY_ZEBRA_THREAD_ID` | Daily Zebra logs. |
| `DISCORD_WEEKLY_ZEBRA_THREAD_ID` | Friday weekly Zebra logs. |
| `DISCORD_ROLLOVER_THREAD_ID` | Futures rollover alerts. |

Every stream requires a thread ID when `DRY_RUN=false`. The bot sends directly to each thread ID.

---

## Futures Rollovers

Rollover alerts are calendar-driven. Add the official expiring contract date, and zInsider computes:

- rollover date: Monday of the expiration week
- early alert: Sunday eight days before rollover Monday
- final alert: Friday immediately before rollover Monday
- alert time: `ROLLOVER_ALERT_HOUR:ROLLOVER_ALERT_MINUTE` in `NY_TIMEZONE`

Standard setup:

```env
DISCORD_ROLLOVER_THREAD_ID=...
ROLLOVER_ENABLED=true
ROLLOVER_ALERT_HOUR=18
ROLLOVER_ALERT_MINUTE=0
ROLLOVER_CALENDAR_PATH=config/rollovers.json
ROLLOVER_CONTRACTS=
```

Calendar format:

```json
{
  "products": [
    {
      "symbol": "ES",
      "contracts": [
        {
          "contract": "ESM2026",
          "expiration_date": "2026-06-19"
        },
        {
          "contract": "ESU2026",
          "expiration_date": "2026-09-18"
        },
        {
          "contract": "ESZ2026",
          "expiration_date": "2026-12-18"
        }
      ]
    }
  ]
}
```

For each product, list contracts in order with their official expiration dates. zInsider derives adjacent rollover pairs automatically, for example `ESM2026 -> ESU2026`, then `ESU2026 -> ESZ2026`.

The product object also accepts `product_name`, `exchange`, `asset_class`, `contract_url`, `notes`, and a free-form `metadata` object. Individual contracts can override `contract_url`, `notes`, or add metadata. Keep official exchange calendars as the source of truth; do not infer expiry dates.

The tracked live calendar is at `config/rollovers.json`; update it only from official exchange calendars. `examples/rollovers.example.json` is the small starter template.

This sends:

```text
ES Futures Rollover — Early heads-up
Roll: ESM2026 → ESU2026
Rollover Monday: 2026-06-15
Expiration: 2026-06-19
```

`ROLLOVER_CONTRACTS` is still available for quick one-off tests:

```env
ROLLOVER_CONTRACTS=ESM2026:2026-06-19:ESU2026
```

Run a rollover check manually with:

```bash
python3 -m app rollovers
```

Use `--force` to print/send configured rollover alerts regardless of the alert date and previous-send state.

The `scheduler` compose service runs the weekday futures scan and the Sunday/Friday rollover checks independently. This matters because the early Sunday alert cannot be produced by a Monday–Friday scanner.

---

## Optional Discord Presence

To keep the zInsider bot user online, set:

```env
DISCORD_BOT_TOKEN=...
DISCORD_PRESENCE_ENABLED=true
DISCORD_PRESENCE_STATUS=online
DISCORD_PRESENCE_ACTIVITY=zInsider
```

The same bot token is used for message delivery and optional presence.

---

## FX Contract

TradingView should POST JSON to:

```text
POST /webhooks/tradingview
```

Raw OHLC payload:

```json
{
  "secret": "change-me",
  "run_key": "2026-05-23",
  "timeframe": "D",
  "bars": {
    "EU": [
      ["2026-05-21", 1.1310, 1.1360, 1.1280, 1.1340],
      ["2026-05-22", 1.1340, 1.1350, 1.1300, 1.1325]
    ],
    "GU": [
      ["2026-05-21", 1.3500, 1.3560, 1.3480, 1.3530],
      ["2026-05-22", 1.3530, 1.3540, 1.3500, 1.3515]
    ]
  }
}
```

Send at least 12 daily bars per FX symbol.

Two bars are enough for inside day checks, but rounded retest, Zebra, and weekly checks need more history.

zInsider stores these bars, computes the signals on the VPS, then routes digest/model streams to Discord.

---

## Supported FX Tickers

```text
EU, GU, EG, AU, NZD, CHF, CAD, UJ, EJ, GJ
```

These are supplied, stored and rendered as plain TradingView/zInsider tickers.
No Yahoo Finance or Twelve Data FX aliases are supported.

---

## Alternate FX Payload Format

TradingView can also send list rows:

```json
{
  "secret": "change-me",
  "run_key": "2026-05-23",
  "bars": [
    {
      "ticker": "EU",
      "timeframe": "D",
      "date": "2026-05-22",
      "open": 1.134,
      "high": 1.135,
      "low": 1.13,
      "close": 1.1325
    }
  ]
}
```

---

## Commands

Run the webhook server:

```bash
python3 -m app serve
```

Run the futures scanner once:

```bash
python3 -m app scan --force
```

Initialize SQLite:

```bash
python3 -m app init-db
```

Print basic stats:

```bash
python3 -m app stats --limit 20
```

---

## Docker

Create and edit the environment file:

```bash
cp .env.example .env
vim .env
```

Build and run:

```bash
docker compose up -d --build
```

Follow logs:

```bash
docker compose logs -f zinsider
```

Run a one-off futures scan:

```bash
docker compose run --rm zinsider scan --force
```

Stop the stack:

```bash
docker compose down
```

---

## Local Run

Create a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Initialize the database:

```bash
python3 -m app init-db
```

Run the webhook server:

```bash
python3 -m app serve
```

Run a scanner pass:

```bash
python3 -m app scan --force
```

---

## Environment

Common environment values include:

```env
TV_WEBHOOK_SECRET=change-me
DB_PATH=data/zinsider.db
DISCORD_BOT_TOKEN=
DISCORD_DIGEST_THREAD_ID=
DISCORD_ID_THREAD_ID=
DISCORD_IW_THREAD_ID=
DISCORD_RR_PLUS_THREAD_ID=
DISCORD_RR_MINUS_THREAD_ID=
DISCORD_ZEBRA_THREAD_ID=
DISCORD_PRESENCE_ENABLED=false
DISCORD_PRESENCE_STATUS=online
DISCORD_PRESENCE_ACTIVITY=zInsider
```

Keep `.env` out of Git.

---

## Deployment Notes

- Put the service behind nginx or Caddy with HTTPS before pointing TradingView at it.
- Set `TV_WEBHOOK_SECRET` and include it in the Pine alert payload.
- Keep `.env` out of Git.
- Keep Discord bot tokens private.
- SQLite lives at `DB_PATH`.
- Docker maps SQLite persistence to the `data` volume by default.
- Remove committed `__pycache__/` directories and `.pyc` files from Git history/index.

---

## Data Persistence

zInsider uses SQLite for local persistence.

Typical local path:

```text
data/zinsider.db
```

The SQLite database is runtime state and should not be committed.

---

## Security

Do not commit:

- `.env`
- Discord bot tokens
- TradingView webhook secrets
- SQLite database files
- Docker volume data
- runtime logs
- local deployment overrides
- VPS credentials
- API keys

Before committing, check:

```bash
git status
git diff --staged
```

---

## License

```text
Proprietary
```

See:

```text
LICENSE
```

All rights reserved.

Unauthorized copying, redistribution, modification, publication, or commercial use is not permitted.

---

## Maintainer

```text
zSPH
```
