from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from app.modules.config import get_settings
from app.modules.assets import get_assets
from app.modules.market import download_bars
from app.modules.signals import detect_inside_days_eth
from app.modules.retest import detect_rounded_retests
from app.modules.state import get_state, save_state
from app.modules.webhooks import send_discord_message


def _eth_close_date_key(now_ny: datetime) -> str:
    # ETH closes at 17:00 NY. If we're before 17:00, "latest close" is yesterday.
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

    # Keep as-is (your inside day pipeline already works)
    df = download_bars(
        tickers=tickers,
        period=settings["yf_period"],
        interval=settings["yf_interval"],
        max_retries=settings["yf_max_retries"],
        retry_backoff_seconds=settings["yf_retry_backoff_seconds"],
    )

    inside_hits, inside_failures, inside_details = detect_inside_days_eth(df, tickers, settings["ny_timezone"])
    rr_hits, rr_failures, rr_details = detect_rounded_retests(df, tickers)

    role_id = settings.get("discord_role_id", "").strip()
    ping_enabled = settings.get("discord_ping_role", False)

    # Always display the role mention text in the header if role_id is set.
    # Actual ping is controlled by allowed_mentions in send_discord_message().
    role_tag = f"<@&{role_id}>" if role_id else "Role tag"

    lines = [
        role_tag,
        f"# {ny_day_key} Inside Day Summary",
        "",
        "--------------",
        "",
    ]

    # Inside day section (unchanged semantics)
    if inside_hits:
        for t in inside_hits:
            prev_date, curr_date, ph, pl, ch, cl = inside_details[t]
            lines.append(
                f"- **Inside day on `{t}`**  \n"
                f"  `{prev_date}` PDH: `{ph:.5f}` / PDL: `{pl:.5f}`  \n"
                f"  `{curr_date}` DH: `{ch:.5f}` / DL: `{cl:.5f}`"
            )
    else:
        lines.append("- No inside days detected.")

    # Rounded retest section (new feature)
    lines.append("")
    lines.append("**Rounded retest**")
    if rr_hits:
        for t in rr_hits:
            d1, d2, d3, h1, l1, c2, l3 = rr_details[t]
            lines.append(
                f"- **Possible Rounded retest forming on `{t}`**  \n"
                f"  D1 hammer `{d1}` (H/L `{h1:.5f}/{l1:.5f}`)  \n"
                f"  D2 `{d2}` close `{c2:.5f}` > D1 high  \n"
                f"  D3 `{d3}` low `{l3:.5f}` > D1 high"
            )
    else:
        lines.append("- None")

    # Failures (union)
    all_failures = sorted(set(inside_failures + rr_failures))
    if all_failures:
        lines += ["", "**Data unavailable:**"]
        for t in all_failures:
            lines.append(f"- `{t}`")

    message = "\n".join(lines)

    # Send if always_send_summary OR any signal fired
    should_send = settings["always_send_summary"] or bool(inside_hits) or bool(rr_hits)
    if should_send:
        send_discord_message(
            message,
            settings["discord_webhook_url"],
            dry_run=settings["dry_run"],
            role_id=role_id,
            allow_role_ping=ping_enabled,
        )

    state["last_sent_ny_day"] = ny_day_key
    save_state(settings["state_dir"], state)


if __name__ == "__main__":
    run_daily_scan()
