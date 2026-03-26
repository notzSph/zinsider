from __future__ import annotations

import os


def get_settings() -> dict:
    """
    Load runtime configuration from environment variables.
    """
    return {
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        "discord_role_id": os.getenv("DISCORD_ROLE_ID", "").strip(),
        "discord_ping_role": os.getenv("DISCORD_PING_ROLE", "false").strip().lower() in ("1", "true", "yes", "y"),

        "always_send_summary": os.getenv("ALWAYS_SEND_SUMMARY", "true").strip().lower() in ("1", "true", "yes", "y"),
        "dry_run": os.getenv("DRY_RUN", "false").strip().lower() in ("1", "true", "yes", "y"),

        "state_dir": os.getenv("STATE_DIR", "state"),
        "ny_timezone": os.getenv("NY_TIMEZONE", "America/New_York"),

        # Yahoo Finance (non-FX: futures, etc.)
        "yf_period": os.getenv("YF_PERIOD", "12d"),
        "yf_interval": os.getenv("YF_INTERVAL", "1d"),
        "yf_max_retries": int(os.getenv("YF_MAX_RETRIES", "3")),
        "yf_retry_backoff_seconds": float(os.getenv("YF_RETRY_BACKOFF_SECONDS", "2.0")),

        # Twelve Data (FX only)
        "twelve_data_api_key": os.getenv("TWELVE_DATA_API_KEY", "").strip(),
        "td_outputsize": int(os.getenv("TD_OUTPUTSIZE", "20")),
        "td_max_retries": int(os.getenv("TD_MAX_RETRIES", "3")),
        "td_retry_backoff_seconds": float(os.getenv("TD_RETRY_BACKOFF_SECONDS", "2.0")),
        "td_base_url": os.getenv("TD_BASE_URL", "https://api.twelvedata.com").strip(),

        "schedule_dow": os.getenv("SCHEDULE_DOW", "mon-fri"),
        "schedule_hour": int(os.getenv("SCHEDULE_HOUR", "17")),
        "schedule_minute": int(os.getenv("SCHEDULE_MINUTE", "18")),
        "run_on_start": os.getenv("RUN_ON_START", "false").strip().lower() in ("1", "true", "yes", "y"),
    }