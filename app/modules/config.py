from __future__ import annotations

import os


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def get_settings() -> dict:
    """
    Load runtime configuration from environment variables.
    """
    return {
        "discord_daily_digest_thread_id": os.getenv("DISCORD_DAILY_DIGEST_THREAD_ID", "").strip(),
        "discord_weekly_digest_thread_id": os.getenv("DISCORD_WEEKLY_DIGEST_THREAD_ID", "").strip(),
        "discord_id_thread_id": os.getenv("DISCORD_ID_THREAD_ID", "").strip(),
        "discord_iw_thread_id": os.getenv("DISCORD_IW_THREAD_ID", "").strip(),
        "discord_daily_rr_plus_thread_id": os.getenv("DISCORD_DAILY_RR_PLUS_THREAD_ID", "").strip(),
        "discord_daily_rr_minus_thread_id": os.getenv("DISCORD_DAILY_RR_MINUS_THREAD_ID", "").strip(),
        "discord_weekly_rr_plus_thread_id": os.getenv("DISCORD_WEEKLY_RR_PLUS_THREAD_ID", "").strip(),
        "discord_weekly_rr_minus_thread_id": os.getenv("DISCORD_WEEKLY_RR_MINUS_THREAD_ID", "").strip(),
        "discord_daily_bullish_zebra_thread_id": os.getenv("DISCORD_DAILY_BULLISH_ZEBRA_THREAD_ID", "").strip(),
        "discord_daily_bearish_zebra_thread_id": os.getenv("DISCORD_DAILY_BEARISH_ZEBRA_THREAD_ID", "").strip(),
        "discord_weekly_bullish_zebra_thread_id": os.getenv("DISCORD_WEEKLY_BULLISH_ZEBRA_THREAD_ID", "").strip(),
        "discord_weekly_bearish_zebra_thread_id": os.getenv("DISCORD_WEEKLY_BEARISH_ZEBRA_THREAD_ID", "").strip(),
        "discord_rollover_thread_id": os.getenv("DISCORD_ROLLOVER_THREAD_ID", "").strip(),
        "discord_role_id": os.getenv("DISCORD_ROLE_ID", "").strip(),
        "discord_ping_role": os.getenv("DISCORD_PING_ROLE", "false").strip().lower() in ("1", "true", "yes", "y"),
        "discord_bot_token": os.getenv("DISCORD_BOT_TOKEN", "").strip(),
        "discord_presence_enabled": os.getenv("DISCORD_PRESENCE_ENABLED", "true").strip().lower() in ("1", "true", "yes", "y"),
        "discord_presence_status": os.getenv("DISCORD_PRESENCE_STATUS", "idle").strip().lower(),
        "discord_presence_activity": os.getenv("DISCORD_PRESENCE_ACTIVITY", "Cooking Shit..").strip(),

        "always_send_summary": os.getenv("ALWAYS_SEND_SUMMARY", "true").strip().lower() in ("1", "true", "yes", "y"),
        "dry_run": os.getenv("DRY_RUN", "false").strip().lower() in ("1", "true", "yes", "y"),

        "state_dir": os.getenv("STATE_DIR", "state"),
        "db_path": os.getenv("DB_PATH", "data/zinsider.sqlite3"),
        "ny_timezone": os.getenv("NY_TIMEZONE", "America/New_York"),

        "tv_webhook_secret": os.getenv("TV_WEBHOOK_SECRET", "").strip(),
        "platform_api_url": os.getenv("PLATFORM_API_URL", "").strip().rstrip("/"),
        "platform_ingest_token": os.getenv("PLATFORM_INGEST_TOKEN", "").strip(),
        "platform_digest_enabled": os.getenv("PLATFORM_DIGEST_ENABLED", "false").strip().lower() in ("1", "true", "yes", "y"),

        # Yahoo Finance (non-FX: futures, etc.)
        "yf_period": os.getenv("YF_PERIOD", "12d"),
        "yf_interval": os.getenv("YF_INTERVAL", "1d"),
        "yf_max_retries": int(os.getenv("YF_MAX_RETRIES", "3")),
        "yf_retry_backoff_seconds": float(os.getenv("YF_RETRY_BACKOFF_SECONDS", "2.0")),

        "schedule_dow": os.getenv("SCHEDULE_DOW", "mon-fri"),
        "schedule_hour": int(os.getenv("SCHEDULE_HOUR", "17")),
        "schedule_minute": int(os.getenv("SCHEDULE_MINUTE", "18")),
        "run_on_start": os.getenv("RUN_ON_START", "false").strip().lower() in ("1", "true", "yes", "y"),

        "futures_tickers": _csv(os.getenv("FUTURES_TICKERS", "")),

        "rollover_enabled": os.getenv("ROLLOVER_ENABLED", "true").strip().lower() in ("1", "true", "yes", "y"),
        "rollover_alert_hour": int(os.getenv("ROLLOVER_ALERT_HOUR", "18")),
        "rollover_alert_minute": int(os.getenv("ROLLOVER_ALERT_MINUTE", "0")),
        "rollover_contracts": _csv(os.getenv("ROLLOVER_CONTRACTS", "")),
        "rollover_calendar_path": os.getenv("ROLLOVER_CALENDAR_PATH", "config/rollovers.json").strip(),
    }
