from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

InsideDetail = Tuple[str, str, float, float, float, float]
# (prev_bar_date, curr_bar_date, prev_high, prev_low, curr_high, curr_low)


def _detect_inside_on_candles(candles: pd.DataFrame) -> Tuple[bool, InsideDetail | None]:
    """
    Detect an inside bar on the latest closed candle.

    candles must be indexed by bar date/datetime and contain:
      Open, High, Low, Close

    Returns:
      (is_inside, detail)
    """
    if candles is None or candles.empty or len(candles) < 2:
        return False, None

    df = candles.copy()
    df = df[["Open", "High", "Low", "Close"]].dropna()
    if len(df) < 2:
        return False, None

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    prev_bar_date = df.index[-2].strftime("%Y-%m-%d")
    curr_bar_date = df.index[-1].strftime("%Y-%m-%d")

    ph, pl = float(prev["High"]), float(prev["Low"])
    ch, cl = float(curr["High"]), float(curr["Low"])

    detail: InsideDetail = (prev_bar_date, curr_bar_date, ph, pl, ch, cl)
    is_inside = (ch <= ph) and (cl >= pl)

    return is_inside, detail


def detect_inside(
    raw_df,
    tickers: List[str],
    build,
):
    """
    Generic inside-bar detector using an external candle builder.

    build(raw_df, ticker) -> DataFrame indexed by closed bar date/string
    with columns: Open, High, Low, Close

    Returns:
        hits: list[str]
            Tickers with inside setup
        failures: list[str]
            Tickers where data was unavailable or invalid
        details: dict[str, tuple[str, str, float, float, float, float]]
            ticker -> (prev_bar_date, curr_bar_date, prev_high, prev_low, curr_high, curr_low)
    """
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, InsideDetail] = {}

    if raw_df is None:
        return hits, tickers[:], details

    for t in tickers:
        try:
            candles = build(raw_df, t)
            if candles is None or candles.empty or len(candles) < 2:
                failures.append(t)
                continue

            is_inside, det = _detect_inside_on_candles(candles)
            if det is None:
                failures.append(t)
                continue

            details[t] = det
            if is_inside:
                hits.append(t)

        except Exception:
            failures.append(t)

    return hits, failures, details


def format_inside(
    title: str,
    hits,
    failures,
    details,
    prev_tag: str,
    curr_tag: str,
) -> List[str]:
    lines: List[str] = [f"## {title}"]

    if hits:
        for t in hits:
            prev_bar_date, curr_bar_date, ph, pl, ch, cl = details[t]
            lines.append(
                f"- **Inside** on `{t}`  \n"
                f"  {prev_tag} `{prev_bar_date}` → H/L `{ph:.5f}` / `{pl:.5f}`  \n"
                f"  {curr_tag} `{curr_bar_date}` → H/L `{ch:.5f}` / `{cl:.5f}`"
            )
    else:
        lines.append("- None")

    return lines
