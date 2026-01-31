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

        "yf_period": os.getenv("YF_PERIOD", "12d"),
        "yf_interval": os.getenv("YF_INTERVAL", "1d"),
        "yf_max_retries": int(os.getenv("YF_MAX_RETRIES", "3")),
        "yf_retry_backoff_seconds": float(os.getenv("YF_RETRY_BACKOFF_SECONDS", "2.0")),

        "schedule_dow": os.getenv("SCHEDULE_DOW", "mon-fri"),
        "schedule_hour": int(os.getenv("SCHEDULE_HOUR", "17")),
        "schedule_minute": int(os.getenv("SCHEDULE_MINUTE", "18")),
        "run_on_start": os.getenv("RUN_ON_START", "false").strip().lower() in ("1", "true", "yes", "y"),
    }
