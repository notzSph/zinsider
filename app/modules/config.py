from __future__ import annotations

import os


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def get_settings() -> dict:
    """
    Load runtime configuration from environment variables.
    """
    return {
        "discord_digest_thread_id": os.getenv("DISCORD_DIGEST_THREAD_ID", "").strip(),
        "discord_id_thread_id": os.getenv("DISCORD_ID_THREAD_ID", "").strip(),
        "discord_iw_thread_id": os.getenv("DISCORD_IW_THREAD_ID", "").strip(),
        "discord_rr_thread_id": os.getenv("DISCORD_RR_THREAD_ID", "").strip(),
        "discord_zebra_thread_id": os.getenv("DISCORD_ZEBRA_THREAD_ID", "").strip(),
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

        # Yahoo Finance (non-FX: futures, etc.)
        "yf_period": os.getenv("YF_PERIOD", "12d"),
        "yf_interval": os.getenv("YF_INTERVAL", "1d"),
        "yf_max_retries": int(os.getenv("YF_MAX_RETRIES", "3")),
        "yf_retry_backoff_seconds": float(os.getenv("YF_RETRY_BACKOFF_SECONDS", "2.0")),

        # Twelve Data legacy fallback (kept optional; TV webhook is primary for FX)
        "twelve_data_api_key": os.getenv("TWELVE_DATA_API_KEY", "").strip(),
        "td_outputsize": int(os.getenv("TD_OUTPUTSIZE", "20")),
        "td_max_retries": int(os.getenv("TD_MAX_RETRIES", "3")),
        "td_retry_backoff_seconds": float(os.getenv("TD_RETRY_BACKOFF_SECONDS", "2.0")),
        "td_base_url": os.getenv("TD_BASE_URL", "https://api.twelvedata.com").strip(),

        "schedule_dow": os.getenv("SCHEDULE_DOW", "mon-fri"),
        "schedule_hour": int(os.getenv("SCHEDULE_HOUR", "17")),
        "schedule_minute": int(os.getenv("SCHEDULE_MINUTE", "18")),
        "run_on_start": os.getenv("RUN_ON_START", "false").strip().lower() in ("1", "true", "yes", "y"),

        "futures_tickers": _csv(os.getenv("FUTURES_TICKERS", "")),
    }
