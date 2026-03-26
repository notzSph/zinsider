from __future__ import annotations

import time
from typing import Dict

import pandas as pd
import requests
import yfinance as yf

from app.modules.assets import split_assets


def _to_twelve_symbol(ticker: str) -> str:
    """
    Convert Yahoo FX ticker into Twelve Data forex symbol.

    Example:
      EURUSD=X -> EUR/USD
    """
    t = ticker.strip().upper()
    if t.endswith("=X"):
        core = t[:-2]
        if len(core) == 6 and core.isalpha():
            return f"{core[:3]}/{core[3:]}"
    raise ValueError(f"Unsupported FX ticker format for Twelve Data: {ticker}")


def _drop_weekends(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    return out[out.index.dayofweek < 5]


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


def _normalize_td_values(values: list[dict]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])

    df = pd.DataFrame(values).copy()

    # TD returns newest first
    df = df.iloc[::-1].reset_index(drop=True)

    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")

    df = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        }
    )

    df = _normalize_ohlc(df)
    df = _drop_weekends(df)

    return df


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


def _download_twelve_daily_map(
    tickers: list[str],
    api_key: str,
    outputsize: int,
    max_retries: int,
    retry_backoff_seconds: float,
    base_url: str,
) -> Dict[str, pd.DataFrame]:
    results: Dict[str, pd.DataFrame] = {}

    if not tickers:
        return results

    if not api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is required when FX tickers are configured")

    session = requests.Session()

    for ticker in tickers:
        symbol = _to_twelve_symbol(ticker)
        last_err = None

        for attempt in range(1, max_retries + 1):
            try:
                resp = session.get(
                    f"{base_url}/time_series",
                    params={
                        "symbol": symbol,
                        "interval": "1day",
                        "outputsize": outputsize,
                        "apikey": api_key,
                        "format": "JSON",
                    },
                    timeout=20,
                )
                resp.raise_for_status()

                payload = resp.json()

                if payload.get("status") == "error":
                    raise RuntimeError(
                        f"Twelve Data error for {ticker} ({symbol}): "
                        f"{payload.get('code')} {payload.get('message')}"
                    )

                values = payload.get("values", [])
                results[ticker] = _normalize_td_values(values)

                if results[ticker].empty:
                    print(f"[market] FX returned empty data for {ticker} ({symbol})")

                break

            except Exception as e:
                last_err = e
                if attempt == max_retries:
                    print(f"[market] FX download failed for {ticker} ({symbol}): {last_err}")
                    results[ticker] = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
                else:
                    time.sleep(retry_backoff_seconds * attempt)

    return results


def download_bars(
    tickers: list[str],
    period: str,
    interval: str,
    max_retries: int,
    retry_backoff_seconds: float,
    twelve_data_api_key: str,
    td_outputsize: int,
    td_max_retries: int,
    td_retry_backoff_seconds: float,
    td_base_url: str,
) -> Dict[str, pd.DataFrame]:
    """
    Mixed downloader:
      - FX -> Twelve Data daily bars
      - everything else -> Yahoo Finance daily bars

    Returns:
        dict[ticker] -> DataFrame(index=date, columns=Open/High/Low/Close)
    """
    if not tickers:
        raise ValueError("tickers is empty")

    fx_tickers, other_tickers = split_assets(tickers)

    results: Dict[str, pd.DataFrame] = {}

    if other_tickers:
        results.update(
            _download_yf_daily_map(
                tickers=other_tickers,
                period=period,
                interval=interval,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
            )
        )

    if fx_tickers:
        results.update(
            _download_twelve_daily_map(
                tickers=fx_tickers,
                api_key=twelve_data_api_key,
                outputsize=td_outputsize,
                max_retries=td_max_retries,
                retry_backoff_seconds=td_retry_backoff_seconds,
                base_url=td_base_url,
            )
        )

    # Ensure every requested ticker exists in the map
    for t in tickers:
        results.setdefault(t, pd.DataFrame(columns=["Open", "High", "Low", "Close"]))

    return results