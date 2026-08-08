from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    run_key TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    meta_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source, run_key)
);

CREATE TABLE IF NOT EXISTS bars (
    provider TEXT NOT NULL,
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    bar_date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    received_at TEXT NOT NULL,
    PRIMARY KEY(provider, ticker, timeframe, bar_date)
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source TEXT NOT NULL,
    signal_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    model TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT '',
    computed_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(source, signal_date, ticker, model, timeframe, direction)
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(path: str):
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def start_run(conn: sqlite3.Connection, source: str, run_key: str, meta: dict | None = None) -> int:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO runs(source, run_key, started_at, status, meta_json)
        VALUES (?, ?, ?, 'running', ?)
        ON CONFLICT(source, run_key) DO UPDATE SET
            started_at=excluded.started_at,
            finished_at=NULL,
            status='running',
            meta_json=excluded.meta_json
        """,
        (source, run_key, now, json.dumps(meta or {}, sort_keys=True)),
    )
    row = conn.execute("SELECT id FROM runs WHERE source=? AND run_key=?", (source, run_key)).fetchone()
    return int(row["id"])


def finish_run(conn: sqlite3.Connection, run_id: int, status: str, meta: dict | None = None) -> None:
    conn.execute(
        "UPDATE runs SET finished_at=?, status=?, meta_json=? WHERE id=?",
        (utc_now(), status, json.dumps(meta or {}, sort_keys=True), run_id),
    )


def store_bars(conn: sqlite3.Connection, provider: str, ticker: str, timeframe: str, candles: Any) -> int:
    if candles is None or candles.empty:
        return 0

    import pandas as pd

    now = utc_now()
    count = 0
    df = candles.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    for idx, row in df.iterrows():
        conn.execute(
            """
            INSERT INTO bars(provider, ticker, timeframe, bar_date, open, high, low, close, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, ticker, timeframe, bar_date) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                received_at=excluded.received_at
            """,
            (
                provider,
                ticker,
                timeframe,
                idx.strftime("%Y-%m-%d"),
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                now,
            ),
        )
        count += 1

    return count


def store_signals(conn: sqlite3.Connection, run_id: int, source: str, signals: Iterable[dict]) -> int:
    # A rerun reuses the same (source, run_key) row. Clear its old snapshot
    # first so resolved setups cannot bleed into a new digest.
    conn.execute("DELETE FROM signals WHERE run_id=?", (run_id,))
    now = utc_now()
    count = 0
    for sig in signals:
        conn.execute(
            """
            INSERT INTO signals(run_id, source, signal_date, ticker, model, timeframe, direction, computed_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, signal_date, ticker, model, timeframe, direction) DO UPDATE SET
                run_id=excluded.run_id,
                computed_json=excluded.computed_json,
                created_at=excluded.created_at
            """,
            (
                run_id,
                source,
                sig["signal_date"],
                sig["ticker"],
                sig["model"],
                sig["timeframe"],
                sig.get("direction", ""),
                json.dumps(sig.get("computed", {}), sort_keys=True),
                now,
            ),
        )
        count += 1
    return count


def recent_signal_counts(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ticker, model, timeframe, direction, COUNT(*) AS count
        FROM signals
        GROUP BY ticker, model, timeframe, direction
        ORDER BY count DESC, ticker ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
