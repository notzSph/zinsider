# zinsider

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Build Status](https://img.shields.io/badge/build-passing-green)
![Python](https://img.shields.io/badge/Python-3.12%2B-informational)
![Docker](https://img.shields.io/badge/Docker-required-informational)
![License: MIT](https://img.shields.io/badge/License-MIT--X-lightgrey)

Daily **inside day** scanner for **FX and futures** (Yahoo Finance via `yfinance`) that posts a single summary message to **Discord**.

## Features

- Runs unattended in Docker
- Schedules on **America/New_York** time (DST-safe)
- Posts a single daily summary message
- Idempotent: avoids duplicate notifications across restarts

## How it works

For each ticker in your universe, the job pulls the last two completed daily bars and flags an **inside day** when:

- `today_high <= yesterday_high` and `today_low >= yesterday_low`

A single Discord message is sent with all tickers that triggered.

## Requirements

- Docker Engine + Docker Compose (v2)
- A Discord server/channel where you can create a webhook
- (Optional) Python 3.12+ if running locally without Docker

## Configuration

### 1) Create a Discord webhook

In your Discord server:

Channel → Edit Channel → Integrations → Webhooks → New Webhook → Copy Webhook URL

Treat the webhook URL as a secret (do not commit it).

### 2) Create your environment file

```bash
cp .env.example .env
```

Edit `.env` and set:

- `DISCORD_WEBHOOK_URL=...`

Common options:

- `ALWAYS_SEND_SUMMARY=true` (send even if no signals)
- `DRY_RUN=true` (log output instead of posting to Discord)

## 3) Edit your asset universe

Update the ticker list in:

- `app/modules/assets.py`

Examples:

- FX: `EURUSD=X`, `USDJPY=X`
- Futures: `ES=F`, `NQ=F`, `CL=F`, `GC=F`

## Deploy with Docker

### Quick start (build + run)

From the repo root:

```bash
docker compose build
docker compose up -d
docker compose logs -f
```

## One-off run (manual)

Trigger a scan immediately:

```bash
docker compose run --rm zinsider
```

If your container runs the scheduler by default and you want a one-shot run:

```bash
docker compose run --rm zinsider
```

## Scheduling

You have two supported ways to schedule; use one (not both).

### Option A: Container scheduler (APScheduler)

Use this if you want scheduling to live entirely inside Docker.

Set in `.env`:

- `NY_TIMEZONE=America/New_York`
- `SCHEDULE_DOW=mon-fri`
- `SCHEDULE_HOUR=17`
- `SCHEDULE_MINUTE=18`

Then run:

```bash
docker compose up -d
```

To confirm scheduling:

```bash
docker compose logs -f
```


You should see a log line indicating the schedule and timezone.

### Option B: Host cron (lowest overhead)

Use this if you prefer the most resource-efficient approach (container starts, runs once, exits).

1) Ensure your compose service runs the one-shot job by default (entrypoint `app.main`).
2) Add a cron entry on the host:

```bash
crontab -e
```

Add:

```bash
TZ=America/New_York
18 17 * * 1-5 cd /opt/zinsider && docker compose run --rm zinsider >> /opt/zinsider/run.log 2>&1
```
Notes:

- `TZ=America/New_York` makes it DST-safe.
- Adjust `/opt/zinsider` to your actual deployment directory.

## Operations

### View logs

```bash
docker compose logs -f
```

### Restart

```bash
docker compose restart
```

### Update / Redeploy

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

### State / idempotency

The app writes a small state file (e.g., `state/state.json` or a mounted Docker volume) to ensure it does not post twice for the same New York session date.

## Security notes

- The Discord webhook URL is the credential. Store it in `.env` and keep it out of Git.
- If the webhook URL is ever exposed, delete/regenerate it in Discord.

## License

MIT (see `LICENSE`).
