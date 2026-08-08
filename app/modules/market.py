from __future__ import annotations

import time
from typing import Dict

import pandas as pd
import yfinance as yf


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])

    out = df.copy()

    keep = [c for c in ["Open", "High", "Low", "Close"] if c in out.columns]
    out = out[keep].copy()

    for c in ["Open", "High", "Low", "Close"]:
        if c not in out.columns:
            out[c] = pd.Series(dtype=float)

    out = out[["Open", "High", "Low", "Close"]].dropna()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    out = out.astype(float)
    return out


def _download_yf_daily_map(
    tickers: list[str],
    period: str,
    interval: str,
    max_retries: int,
    retry_backoff_seconds: float,
) -> Dict[str, pd.DataFrame]:
    results: Dict[str, pd.DataFrame] = {}

    if not tickers:
        return results

    joined = " ".join(tickers)
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            raw = yf.download(
                tickers=joined,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                group_by="column",
                threads=True,
            )

            multi = getattr(raw.columns, "nlevels", 1) > 1

            for t in tickers:
                try:
                    if multi:
                        sub = pd.DataFrame(
                            {
                                "Open": raw["Open"][t],
                                "High": raw["High"][t],
                                "Low": raw["Low"][t],
                                "Close": raw["Close"][t],
                            }
                        )
                    else:
                        sub = raw[["Open", "High", "Low", "Close"]].copy()

                    results[t] = _normalize_ohlc(sub)
                except Exception:
                    results[t] = pd.DataFrame(columns=["Open", "High", "Low", "Close"])

            return results

        except Exception as e:
            last_err = e
            time.sleep(retry_backoff_seconds * attempt)

    raise RuntimeError(f"yfinance download failed after {max_retries} retries: {last_err}")


def download_bars(
    tickers: list[str],
    period: str,
    interval: str,
    max_retries: int,
    retry_backoff_seconds: float,
) -> Dict[str, pd.DataFrame]:
    """
    Download the configured futures universe from Yahoo Finance.

    FX data is supplied only through the TradingView webhook and never enters
    this downloader.

    Returns:
        dict[ticker] -> DataFrame(index=date, columns=Open/High/Low/Close)
    """
    if not tickers:
        raise ValueError("tickers is empty")

    results = _download_yf_daily_map(
        tickers=tickers,
        period=period,
        interval=interval,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )

    # Ensure every requested ticker exists in the map
    for t in tickers:
        results.setdefault(t, pd.DataFrame(columns=["Open", "High", "Low", "Close"]))

    return results
