from __future__ import annotations

import time
import yfinance as yf


def download_daily_bars(
    tickers: list[str],
    period: str,
    interval: str,
    max_retries: int,
    retry_backoff_seconds: float,
):
    """
    Download daily OHLCV bars for multiple tickers using yfinance.
    """
    if not tickers:
        raise ValueError("tickers is empty")

    joined = " ".join(tickers)
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            return yf.download(
                tickers=joined,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                group_by="column",
                threads=True,
            )
        except Exception as e:
            last_err = e
            time.sleep(retry_backoff_seconds * attempt)

    raise RuntimeError(f"yfinance download failed after {max_retries} retries: {last_err}")
