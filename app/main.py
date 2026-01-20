from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.modules.config import get_settings
from app.modules.assets import get_assets
from app.modules.market import download_daily_bars
from app.modules.signals import detect_inside_days
from app.modules.state import get_state, save_state
from app.modules.webhooks import send_discord_message


def run_daily_scan() -> None:
    settings = get_settings()
    tickers = get_assets()

    if not tickers:
        raise RuntimeError("Asset universe is empty. Update app/modules/assets.py")

    ny_tz = ZoneInfo(settings["ny_timezone"])
    ny_day_key = datetime.now(ny_tz).strftime("%Y-%m-%d")

    state = get_state(settings["state_dir"])
    if state.get("last_sent_ny_day") == ny_day_key:
        return

    df = download_daily_bars(
        tickers=tickers,
        period=settings["yf_period"],
        interval=settings["yf_interval"],
        max_retries=settings["yf_max_retries"],
        retry_backoff_seconds=settings["yf_retry_backoff_seconds"],
    )

    hits, failures, details = detect_inside_days(df, tickers)

    lines = [f"Inside day summary (NY session date: {ny_day_key})", ""]

    if hits:
        for t in hits:
            prev_date, curr_date, ph, pl, ch, cl = details[t]
            lines.append(
                f"Inside day on {t} "
                f"(prev {prev_date} H/L {ph:.5f}/{pl:.5f}, "
                f"curr {curr_date} H/L {ch:.5f}/{cl:.5f})"
            )
    else:
        lines.append("No inside days detected.")

    if failures:
        lines += ["", "Data unavailable:"]
        for t in sorted(set(failures)):
            lines.append(f"- {t}")

    message = "\n".join(lines)

    if settings["always_send_summary"] or bool(hits):
        send_discord_message(message, settings["discord_webhook_url"], dry_run=settings["dry_run"])

    state["last_sent_ny_day"] = ny_day_key
    save_state(settings["state_dir"], state)


if __name__ == "__main__":
    run_daily_scan()
