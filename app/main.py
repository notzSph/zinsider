from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from app.modules.analyzer import analyze_daily_map
from app.modules.assets import get_futures
from app.modules.config import get_settings
from app.modules.db import (
    connect,
    finish_run,
    start_run,
    store_bars,
    store_signals,
)
from app.modules.market import download_bars
from app.modules.render import (
    DAILY_MODEL_ORDER,
    WEEKLY_MODEL_ORDER,
    STREAM_THREADS,
    render_digest,
    render_stream,
)
from app.modules.state import get_state, save_state
from app.modules.webhooks import send_discord_message


def _eth_close_date_key(now_ny: datetime) -> str:
    close_time = dtime(hour=17, minute=0)
    if now_ny.time() < close_time:
        now_ny = now_ny - timedelta(days=1)
    return now_ny.strftime("%Y-%m-%d")


def _post_outputs(
    settings: dict,
    digest_signals: list[dict],
    stream_signals: list[dict],
    failures: list[str],
    source: str,
    include_weekly: bool,
) -> None:
    role_id = settings.get("discord_role_id", "").strip()
    ping_enabled = settings.get("discord_ping_role", False)

    labelled_digest_signals = [{**signal, "source": source} for signal in digest_signals]
    daily_signals = [signal for signal in labelled_digest_signals if signal["model"] in DAILY_MODEL_ORDER]
    weekly_signals = [signal for signal in labelled_digest_signals if signal["model"] in WEEKLY_MODEL_ORDER]

    if settings["always_send_summary"] or daily_signals or failures:
        send_discord_message(
            render_digest("**zInsider Daily Market Digest**", daily_signals, failures, DAILY_MODEL_ORDER),
            settings["discord_bot_token"],
            settings.get(STREAM_THREADS["daily_digest"], ""),
            dry_run=settings["dry_run"],
            role_id=role_id,
            allow_role_ping=ping_enabled,
        )

    for model in DAILY_MODEL_ORDER:
        content = render_stream(model, stream_signals, source=source)
        if not content:
            continue
        send_discord_message(
            content,
            settings["discord_bot_token"],
            settings.get(STREAM_THREADS[model], ""),
            dry_run=settings["dry_run"],
            role_id=role_id,
            allow_role_ping=False,
        )

    if include_weekly:
        send_discord_message(
            render_digest("**zInsider Weekly Market Digest**", weekly_signals, [], WEEKLY_MODEL_ORDER),
            settings["discord_bot_token"],
            settings.get(STREAM_THREADS["weekly_digest"], ""),
            dry_run=settings["dry_run"],
            role_id=role_id,
            allow_role_ping=ping_enabled,
        )
        for model in WEEKLY_MODEL_ORDER:
            content = render_stream(model, stream_signals, source=source)
            if not content:
                continue
            send_discord_message(
                content,
                settings["discord_bot_token"],
                settings.get(STREAM_THREADS[model], ""),
                dry_run=settings["dry_run"],
                role_id=role_id,
                allow_role_ping=False,
            )


def run_futures_scan(force: bool = False) -> dict:
    settings = get_settings()
    tickers = get_futures(settings)

    if not tickers:
        raise RuntimeError("Futures universe is empty. Set FUTURES_TICKERS or update app/modules/assets.py")

    ny_tz = ZoneInfo(settings["ny_timezone"])
    now_ny = datetime.now(ny_tz)
    ny_day_key = _eth_close_date_key(now_ny)

    state = get_state(settings["state_dir"])
    if not force and state.get("last_sent_futures_ny_day") == ny_day_key:
        return {"status": "skipped", "run_key": ny_day_key}

    df_map = download_bars(
        tickers=tickers,
        period=settings["yf_period"],
        interval=settings["yf_interval"],
        max_retries=settings["yf_max_retries"],
        retry_backoff_seconds=settings["yf_retry_backoff_seconds"],
    )

    include_weekly = now_ny.weekday() == 4
    signals, failures = analyze_daily_map(df_map, tickers, include_weekly=include_weekly)

    with connect(settings["db_path"]) as conn:
        run_id = start_run(conn, "yfinance", ny_day_key, {"tickers": tickers})
        bars_written = 0
        for ticker, candles in df_map.items():
            bars_written += store_bars(conn, "yfinance", ticker, "D", candles)
        signals_written = store_signals(conn, run_id, "yfinance", signals)
        finish_run(
            conn,
            run_id,
            "ok",
            {"bars": bars_written, "signals": signals_written, "failures": failures},
        )
    _post_outputs(
        settings,
        signals,
        signals,
        failures,
        source="yfinance",
        include_weekly=include_weekly,
    )

    state["last_sent_futures_ny_day"] = ny_day_key
    save_state(settings["state_dir"], state)

    return {
        "status": "ok",
        "run_key": ny_day_key,
        "tickers": len(tickers),
        "signals": len(signals),
        "failures": len(failures),
    }


def run_daily_scan() -> None:
    run_futures_scan()


if __name__ == "__main__":
    print(run_futures_scan(force=True))
