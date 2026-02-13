from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from app.modules.config import get_settings
from app.modules.assets import get_assets
from app.modules.market import download_bars
from app.modules.inside import detect_inside, format_inside
from app.modules.signals import candles_day_eth, candles_week_from_day
from app.modules.retest import detect_rounded_retests
from app.modules.state import get_state, save_state
from app.modules.webhooks import send_discord_message


def _eth_close_date_key(now_ny: datetime) -> str:
    close_time = dtime(hour=17, minute=0)
    if now_ny.time() < close_time:
        now_ny = now_ny - timedelta(days=1)
    return now_ny.strftime("%Y-%m-%d")


def run_daily_scan() -> None:
    settings = get_settings()
    tickers = get_assets()

    if not tickers:
        raise RuntimeError("Asset universe is empty. Update app/modules/assets.py")

    ny_tz = ZoneInfo(settings["ny_timezone"])
    now_ny = datetime.now(ny_tz)
    ny_day_key = _eth_close_date_key(now_ny)

    state = get_state(settings["state_dir"])
    if state.get("last_sent_ny_day") == ny_day_key:
        return

    df = download_bars(
        tickers=tickers,
        period=settings["yf_period"],
        interval=settings["yf_interval"],
        max_retries=settings["yf_max_retries"],
        retry_backoff_seconds=settings["yf_retry_backoff_seconds"],
    )

    # Inside day via generic pipeline (same ETH day candles)
    day_hits, day_fail, day_det = detect_inside(
        df, tickers, build=lambda raw, t: candles_day_eth(raw, t, settings["ny_timezone"])
    )

    # Rounded retest (bull + bear)
    rr_hits, rr_fail, rr_det = detect_rounded_retests(df, tickers)

    # Inside week: only after weekly close (Friday >= 17:00 NY), once per week
    week_hits, week_fail, week_det = [], [], {}
    friday_close = (now_ny.weekday() == 4) and (now_ny.time() >= dtime(hour=17, minute=0))
    ny_week_key = now_ny.strftime("%G-W%V")

    if friday_close and state.get("last_sent_ny_week") != ny_week_key:
        week_hits, week_fail, week_det = detect_inside(
            df,
            tickers,
            build=lambda raw, t: candles_week_from_day(raw, t, settings["ny_timezone"], min_days=3),
        )

    role_id = settings.get("discord_role_id", "").strip()
    ping_enabled = settings.get("discord_ping_role", False)
    role_tag = f"<@&{role_id}>" if role_id else "Role tag"

    lines = [
        role_tag,
        f"# {ny_day_key} Summary",
        "",
        "--------------",
        "",
    ]

    lines += format_inside("Inside day", day_hits, day_fail, day_det, prev_tag="PDH/PDL", curr_tag="DH/DL")

    lines.append("")
    lines.append("**Rounded retest**")
    if rr_hits:
        for t in rr_hits:
            direction, d1, d2, d3, h1, l1, c2, lvl3 = rr_det[t]
            if direction == "bull":
                lines.append(
                    f"- **Possible Rounded retest (bullish)** on `{t}`  \n"
                    f"  D1 hammer `{d1}` (H/L `{h1:.5f}/{l1:.5f}`)  \n"
                    f"  D2 `{d2}` close `{c2:.5f}` > D1 high  \n"
                    f"  D3 `{d3}` low `{lvl3:.5f}` > D1 high"
                )
            else:
                lines.append(
                    f"- **Possible Rounded retest (bearish)** on `{t}`  \n"
                    f"  D1 shooting star `{d1}` (H/L `{h1:.5f}/{l1:.5f}`)  \n"
                    f"  D2 `{d2}` close `{c2:.5f}` < D1 low  \n"
                    f"  D3 `{d3}` high `{lvl3:.5f}` < D1 low"
                )
    else:
        lines.append("- None")

    if friday_close:
        lines.append("")
        lines += format_inside("Inside week", week_hits, week_fail, week_det, prev_tag="PWH/PWL", curr_tag="WH/WL")

    # optional: union failures
    all_failures = sorted(set(day_fail + rr_fail + week_fail))
    if all_failures:
        lines += ["", "**Data unavailable:**"]
        for t in all_failures:
            lines.append(f"- `{t}`")

    message = "\n".join(lines)

    should_send = (
        settings["always_send_summary"]
        or bool(day_hits)
        or bool(rr_hits)
        or (friday_close and bool(week_hits))
    )

    if should_send:
        send_discord_message(
            message,
            settings["discord_webhook_url"],
            dry_run=settings["dry_run"],
            role_id=role_id,
            allow_role_ping=ping_enabled,
        )

    state["last_sent_ny_day"] = ny_day_key
    if friday_close:
        state["last_sent_ny_week"] = ny_week_key
    save_state(settings["state_dir"], state)


if __name__ == "__main__":
    run_daily_scan()
