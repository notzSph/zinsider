from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from app.modules.assets import get_assets
from app.modules.config import get_settings
from app.modules.inside import detect_inside, format_inside
from app.modules.market import download_bars
from app.modules.retest import detect_rounded_retests
from app.modules.signals import candles_week_from_day_direct
from app.modules.state import get_state, save_state
from app.modules.webhooks import send_discord_message
from app.modules.zebra import detect_zebra, format_zebra


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
        twelve_data_api_key=settings["twelve_data_api_key"],
        td_outputsize=settings["td_outputsize"],
        td_max_retries=settings["td_max_retries"],
        td_retry_backoff_seconds=settings["td_retry_backoff_seconds"],
        td_base_url=settings["td_base_url"],
    )

    # Inside day via generic pipeline on normalized daily OHLC per ticker
    day_hits, day_fail, day_det = detect_inside(
        df,
        tickers,
        build=lambda raw, t: raw.get(t),
    )

    # Rounded retest (bull + bear)
    rr_hits, rr_fail, rr_det = detect_rounded_retests(df, tickers)

    # Zebra day: alert on the 6th bar setup using daily candles
    zebra_day_hits, zebra_day_fail, zebra_day_det = detect_zebra(
        df,
        tickers,
        build=lambda raw, t: raw.get(t),
    )

    # Weekly scans: only after weekly close (Friday >= 17:00 NY), once per week
    week_hits, week_fail, week_det = [], [], {}
    zebra_week_hits, zebra_week_fail, zebra_week_det = [], [], {}

    friday_close = (now_ny.weekday() == 4) and (now_ny.time() >= dtime(hour=17, minute=0))

    ny_week_key = now_ny.strftime("%G-W%V")
    week_num = int(now_ny.strftime("%V"))
    week_year = int(now_ny.strftime("%G"))
    week_title = f"Week {week_num} ({week_year}) Summary"

    if friday_close and state.get("last_sent_ny_week") != ny_week_key:
        week_hits, week_fail, week_det = detect_inside(
            df,
            tickers,
            build=lambda raw, t: candles_week_from_day_direct(raw.get(t), min_days=3),
        )

        zebra_week_hits, zebra_week_fail, zebra_week_det = detect_zebra(
            df,
            tickers,
            build=lambda raw, t: candles_week_from_day_direct(raw.get(t), min_days=3),
        )

    role_id = settings.get("discord_role_id", "").strip()
    ping_enabled = settings.get("discord_ping_role", False)
    role_tag = f"<@&{role_id}>" if role_id else "Role tag"

    lines = [
        role_tag,
        f"# {ny_day_key} zInsider Summary",
        "",
        "─────────────────────────────────",
    ]

    lines += format_inside(
        "Inside day",
        day_hits,
        day_fail,
        day_det,
        prev_tag="PDH/PDL",
        curr_tag="DH/DL",
    )

    lines.append("")
    lines.append("────────────────")
    lines.append("")
    lines.append("## Rounded Retest")

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

    lines.append("")
    lines.append("────────────────")
    lines.append("")
    lines += format_zebra(
        "Daily Zebra",
        zebra_day_hits,
        zebra_day_fail,
        zebra_day_det,
        timeframe_tag="Day",
    )

    if friday_close:
        lines.append("")
        lines.append("────────────────")
        lines.append("")
        lines.append(f"## {week_title}")
        lines.append("")
        lines += format_inside(
            "Inside week",
            week_hits,
            week_fail,
            week_det,
            prev_tag="PWH/PWL",
            curr_tag="WH/WL",
        )

        lines.append("")
        lines.append("────────────────")
        lines.append("")
        lines += format_zebra(
            "Weekly Zebra",
            zebra_week_hits,
            zebra_week_fail,
            zebra_week_det,
            timeframe_tag="Week",
        )

    all_failures = sorted(
        set(
            day_fail
            + rr_fail
            + zebra_day_fail
            + (week_fail if friday_close else [])
            + (zebra_week_fail if friday_close else [])
        )
    )

    if all_failures:
        lines += ["", "**Data unavailable:**"]
        for t in all_failures:
            lines.append(f"- `{t}`")

    message = "\n".join(lines)

    should_send = (
        settings["always_send_summary"]
        or bool(day_hits)
        or bool(rr_hits)
        or bool(zebra_day_hits)
        or (friday_close and bool(week_hits))
        or (friday_close and bool(zebra_week_hits))
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
