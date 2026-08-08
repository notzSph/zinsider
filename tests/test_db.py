from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.modules.db import connect, finish_run, start_run, store_signals


def _signal(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "model": "ID",
        "timeframe": "D",
        "signal_date": "2026-08-08",
        "computed": {},
    }


class SignalStorageTests(unittest.TestCase):
    def test_rerun_replaces_its_old_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "zinsider.sqlite3")
            with connect(path) as conn:
                run_id = start_run(conn, "yfinance", "2026-08-08")
                store_signals(conn, run_id, "yfinance", [_signal("GBPUSD=X")])
                store_signals(conn, run_id, "yfinance", [_signal("YM=F")])
                finish_run(conn, run_id, "ok")

                rows = conn.execute("SELECT ticker FROM signals WHERE run_id=?", (run_id,)).fetchall()

            self.assertEqual([row["ticker"] for row in rows], ["YM=F"])
