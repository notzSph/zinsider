from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from flask import Flask, jsonify, request

from app.modules.analyzer import analyze_daily_map
from app.modules.assets import normalize_ticker
from app.modules.config import get_settings
from app.modules.db import (
    connect,
    finish_run,
    start_run,
    store_bars,
    store_signals,
)
from app.modules.render import (
    DAILY_MODEL_ORDER,
    WEEKLY_MODEL_ORDER,
    STREAM_THREADS,
    render_digest,
    render_stream,
)
from app.modules.webhooks import send_discord_message


def _bar_frame(rows: list[dict]) -> pd.DataFrame:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "date": row["date"],
                "Open": float(row["open"]),
                "High": float(row["high"]),
                "Low": float(row["low"]),
                "Close": float(row["close"]),
            }
        )

    df = pd.DataFrame(normalized)
    if df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df[["Open", "High", "Low", "Close"]]


def _rows_from_payload(payload: dict[str, Any]) -> list[dict]:
    bars = payload.get("bars", [])

    if isinstance(bars, list):
        return bars

    if not isinstance(bars, dict):
        raise ValueError("bars must be a list or object")

    rows: list[dict] = []
    default_timeframe = str(payload.get("timeframe", "D")).upper()

    for ticker, ticker_bars in bars.items():
        for item in ticker_bars:
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("ticker", ticker)
                row.setdefault("timeframe", default_timeframe)
            else:
                date, open_, high, low, close = item
                row = {
                    "ticker": ticker,
                    "timeframe": default_timeframe,
                    "date": date,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            rows.append(row)

    return rows


def _post(
    settings: dict,
    digest_signals: list[dict],
    stream_signals: list[dict],
    failures: list[str],
    source: str,
    include_weekly: bool,
) -> None:
    role_id = settings.get("discord_role_id", "").strip()
    labelled_digest_signals = [{**signal, "source": source} for signal in digest_signals]
    daily_signals = [signal for signal in labelled_digest_signals if signal["model"] in DAILY_MODEL_ORDER]
    weekly_signals = [signal for signal in labelled_digest_signals if signal["model"] in WEEKLY_MODEL_ORDER]

    send_discord_message(
        render_digest("**zInsider Daily Market Digest**", daily_signals, failures, DAILY_MODEL_ORDER),
        settings["discord_bot_token"],
        settings.get(STREAM_THREADS["daily_digest"], ""),
        dry_run=settings["dry_run"],
        role_id=role_id,
        allow_role_ping=settings.get("discord_ping_role", False),
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
        )

    if include_weekly:
        send_discord_message(
            render_digest("**zInsider Weekly Market Digest**", weekly_signals, [], WEEKLY_MODEL_ORDER),
            settings["discord_bot_token"],
            settings.get(STREAM_THREADS["weekly_digest"], ""),
            dry_run=settings["dry_run"],
            role_id=role_id,
            allow_role_ping=settings.get("discord_ping_role", False),
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
            )


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True})

    @app.post("/webhooks/tradingview")
    def tradingview_webhook():
        settings = get_settings()
        payload = request.get_json(force=True, silent=False)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "invalid json payload"}), 400

        secret = settings.get("tv_webhook_secret", "")
        if secret and payload.get("secret") != secret:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

        try:
            rows = _rows_from_payload(payload)
        except (KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        if not rows:
            return jsonify({"ok": False, "error": "no bars supplied"}), 400

        frames: dict[tuple[str, str], list[dict]] = {}
        for row in rows:
            ticker = normalize_ticker(str(row["ticker"]))
            timeframe = str(row.get("timeframe", payload.get("timeframe", "D"))).upper()
            frames.setdefault((ticker, timeframe), []).append(row)

        daily_map: dict[str, pd.DataFrame] = {}
        tickers: list[str] = []
        bars_written = 0
        generated_at = str(payload.get("generated_at") or "")
        run_key = str(
            payload.get("run_key")
            or payload.get("date")
            or (generated_at[:10] if generated_at else "")
            or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        with connect(settings["db_path"]) as conn:
            run_id = start_run(conn, "tradingview", run_key, {"rows": len(rows)})

            for (ticker, timeframe), frame_rows in frames.items():
                candles = _bar_frame(frame_rows)
                bars_written += store_bars(conn, "tradingview", ticker, timeframe, candles)
                if timeframe == "D":
                    daily_map[ticker] = candles
                    tickers.append(ticker)

            now_ny = datetime.now(ZoneInfo(settings["ny_timezone"]))
            include_weekly = now_ny.weekday() == 4
            signals, failures = analyze_daily_map(
                daily_map,
                sorted(set(tickers)),
                include_weekly=include_weekly,
            )
            signals_written = store_signals(conn, run_id, "tradingview", signals)
            finish_run(
                conn,
                run_id,
                "ok",
                {"bars": bars_written, "signals": signals_written, "failures": failures},
            )
        _post(
            settings,
            signals,
            signals,
            failures,
            source="tradingview",
            include_weekly=include_weekly,
        )

        return jsonify(
            {
                "ok": True,
                "run_key": run_key,
                "bars": bars_written,
                "signals": len(signals),
                "failures": failures,
            }
        )

    return app


app = create_app()
