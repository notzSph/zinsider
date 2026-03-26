from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Literal

import pandas as pd

Direction = Literal["bull", "bear"]

RoundedDetail = Tuple[Direction, str, str, str, float, float, float, float]

ExtractedThree = Tuple[
    str, str, str,                 # d1_date, d2_date, d3_date
    float, float, float, float,    # d1_o, d1_h, d1_l, d1_c
    float, float, float, float,    # d2_o, d2_h, d2_l, d2_c
    float, float, float, float,    # d3_o, d3_h, d3_l, d3_c
]


def is_hammer(open_: float, high: float, low: float, close: float) -> bool:
    """
    Stricter hammer:
      - small real body
      - long lower wick
      - very small upper wick
      - BOTH open and close in upper part of the range
    """
    rng = high - low
    if rng <= 0:
        return False

    body = abs(close - open_)
    body = max(body, rng * 0.01)

    upper = high - max(open_, close)
    lower = min(open_, close) - low

    if body / rng > 0.30:
        return False

    if lower < 2.5 * body:
        return False

    if upper > 0.5 * body:
        return False

    upper_threshold = low + 0.65 * rng
    if min(open_, close) < upper_threshold:
        return False

    return True


def is_shooting_star(open_: float, high: float, low: float, close: float) -> bool:
    """
    Stricter shooting star:
      - small real body
      - long upper wick
      - very small lower wick
      - BOTH open and close in lower part of the range
    """
    rng = high - low
    if rng <= 0:
        return False

    body = abs(close - open_)
    body = max(body, rng * 0.01)

    upper = high - max(open_, close)
    lower = min(open_, close) - low

    if body / rng > 0.30:
        return False

    if upper < 2.5 * body:
        return False

    if lower > 0.5 * body:
        return False

    lower_threshold = low + 0.35 * rng
    if max(open_, close) > lower_threshold:
        return False

    return True


def _coerce_to_daily(candles: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure one OHLC bar per calendar day.

    If intraday bars are accidentally passed in, collapse them to daily:
      Open  = first
      High  = max
      Low   = min
      Close = last
    """
    if candles is None or candles.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])

    df = candles.copy()
    df = df[["Open", "High", "Low", "Close"]].dropna()

    if df.empty:
        return df

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    daily_key = df.index.normalize()
    df = (
        df.groupby(daily_key, sort=True)
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        })
        .dropna()
    )

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


def _extract_last_three(candles: pd.DataFrame) -> Optional[ExtractedThree]:
    """
    candles must have columns: Open, High, Low, Close
    """
    if candles is None or candles.empty:
        return None

    df = _coerce_to_daily(candles)

    if len(df) < 3:
        return None

    d1 = df.iloc[-3]
    d2 = df.iloc[-2]
    d3 = df.iloc[-1]

    d1_date = df.index[-3].strftime("%Y-%m-%d")
    d2_date = df.index[-2].strftime("%Y-%m-%d")
    d3_date = df.index[-1].strftime("%Y-%m-%d")

    return (
        d1_date, d2_date, d3_date,
        float(d1["Open"]), float(d1["High"]), float(d1["Low"]), float(d1["Close"]),
        float(d2["Open"]), float(d2["High"]), float(d2["Low"]), float(d2["Close"]),
        float(d3["Open"]), float(d3["High"]), float(d3["Low"]), float(d3["Close"]),
    )


def detect_rounded_retests(df_map, tickers: List[str]):
    """
    Rounded retest (3-day spec), both directions.

    df_map:
        dict[ticker] -> DataFrame(index=date, columns=Open/High/Low/Close)

    Bullish:
      1) D1 hammer
      2) D2 close > D1 high
      3) D3 low > D1 high

    Bearish:
      1) D1 shooting star
      2) D2 close < D1 low
      3) D3 high < D1 low
    """
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, RoundedDetail] = {}

    if not df_map:
        return hits, tickers[:], details

    for t in tickers:
        try:
            candles = df_map.get(t)
            extracted = _extract_last_three(candles)
            if not extracted:
                failures.append(t)
                continue

            (
                d1_date, d2_date, d3_date,
                d1_o, d1_h, d1_l, d1_c,
                _d2_o, _d2_h, _d2_l, d2_c,
                _d3_o, d3_h, d3_l, _d3_c,
            ) = extracted

            if is_hammer(d1_o, d1_h, d1_l, d1_c):
                if (d2_c > d1_h) and (d3_l > d1_h):
                    hits.append(t)
                    details[t] = ("bull", d1_date, d2_date, d3_date, d1_h, d1_l, d2_c, d3_l)
                    continue

            if is_shooting_star(d1_o, d1_h, d1_l, d1_c):
                if (d2_c < d1_l) and (d3_h < d1_l):
                    hits.append(t)
                    details[t] = ("bear", d1_date, d2_date, d3_date, d1_h, d1_l, d2_c, d3_h)
                    continue

        except Exception:
            failures.append(t)

    return hits, failures, details