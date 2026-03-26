from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

ZebraDetail = Tuple[str, str]
# (curr_bar_date, pattern_matched)
# pattern_matched is one of:
# - "Up/Down/Up/Down/Up/Down"   -> bearish setup
# - "Down/Up/Down/Up/Down/Up"   -> bullish setup


def _dir(open_: float, close: float) -> str | None:
    """
    Candle-body direction:
      - Up   if close > open
      - Down if close < open
      - None if doji / equal
    """
    if close > open_:
        return "Up"
    if close < open_:
        return "Down"
    return None


def _detect_zebra_on_candles(candles: pd.DataFrame) -> Tuple[str | None, ZebraDetail | None]:
    """
    Detect Zebra setup on the latest fully closed candle.

    Requires at least 6 closed candles -> 6 candle-body directions.

    Bearish setup:
        Up / Down / Up / Down / Up / Down
    Bullish setup:
        Down / Up / Down / Up / Down / Up

    We alert on the 6th bar in the sequence, i.e. the latest fully closed bar
    in the 6-candle window, because the next bar is the one we want to catch
    in the same direction as bar 6.
    """
    if candles is None or candles.empty:
        return None, None

    candles = candles.copy()
    candles = candles[["Open", "High", "Low", "Close"]].dropna()
    if candles.empty:
        return None, None

    candles.index = pd.to_datetime(candles.index)
    candles = candles.sort_index()

    # Drop today's bar if present; vendor daily FX feeds often include
    # the current in-progress day, which should not be used for pattern detection.
    today = pd.Timestamp.now().normalize()
    if len(candles) > 0 and candles.index[-1].normalize() >= today:
        candles = candles.iloc[:-1]

    if len(candles) < 6:
        return None, None

    last6 = candles.iloc[-6:].copy()

    opens = last6["Open"].astype(float).tolist()
    closes = last6["Close"].astype(float).tolist()

    dirs: List[str] = []
    for open_, close in zip(opens, closes):
        d = _dir(open_, close)
        if d is None:
            return None, None
        dirs.append(d)

    if dirs == ["Up", "Down", "Up", "Down", "Up", "Down"]:
        curr_bar_date = last6.index[-1].strftime("%Y-%m-%d")
        return "bearish", (curr_bar_date, "Up/Down/Up/Down/Up/Down")

    if dirs == ["Down", "Up", "Down", "Up", "Down", "Up"]:
        curr_bar_date = last6.index[-1].strftime("%Y-%m-%d")
        return "bullish", (curr_bar_date, "Down/Up/Down/Up/Down/Up")

    return None, None


def detect_zebra(
    df_hourly,
    tickers: List[str],
    build,
):
    """
    Generic Zebra detector using an external candle builder.

    build(raw_df, ticker) -> DataFrame indexed by closed bar date/string
    with columns: Open, High, Low, Close

    Returns:
        hits: list[str]
            Tickers with Zebra setup
        failures: list[str]
            Tickers where data was unavailable or invalid
        details: dict[str, tuple[str, str, str]]
            ticker -> (direction, curr_bar_date, matched_pattern)
    """
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, Tuple[str, str, str]] = {}

    if df_hourly is None or len(df_hourly) == 0:
        return hits, tickers[:], details

    for t in tickers:
        try:
            candles = build(df_hourly, t)
            if candles is None or candles.empty:
                failures.append(t)
                continue

            direction, det = _detect_zebra_on_candles(candles)
            if direction is None or det is None:
                continue

            curr_bar_date, matched_pattern = det
            hits.append(t)
            details[t] = (direction, curr_bar_date, matched_pattern)

        except Exception:
            failures.append(t)

    return hits, failures, details


def format_zebra(title: str, hits, failures, details, timeframe_tag: str) -> List[str]:
    lines: List[str] = [f"## {title}"]

    if hits:
        for t in hits:
            direction, curr_bar_date, matched_pattern = details[t]
            expected = "Down" if direction == "bearish" else "Up"
            lines.append(
                f"- **Zebra setup ({direction})** on `{t}`  \n"
                f"  {timeframe_tag} `{curr_bar_date}`  \n"
                f"  Pattern `{matched_pattern}`  \n"
                f"  Watching next {timeframe_tag.lower()} close for `{expected}` continuation"
            )
    else:
        lines.append("- None")

    return lines