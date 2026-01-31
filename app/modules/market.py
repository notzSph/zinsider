from __future__ import annotations

import time
import yfinance as yf


def download_bars(
    tickers: list[str],
    period: str,
    interval: str,
    max_retries: int,
    retry_backoff_seconds: float,
):
    """
    Generic yfinance downloader. Use:
      - period=14d interval=60m for ETH-session aggregation
      - (avoid 1d for FX if you care about 18:00->17:00 NY semantics)
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
