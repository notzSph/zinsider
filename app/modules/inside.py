from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import pandas as pd

InsideDetail = Tuple[str, str, float, float, float, float]
# (prev_label, curr_label, prev_high, prev_low, curr_high, curr_low)

CandleBuilder = Callable[[pd.DataFrame, str], pd.DataFrame]
# (raw_df, ticker) -> candles_df with columns Open/High/Low/Close, index label strings


def detect_inside(raw_df: pd.DataFrame, tickers: List[str], build: CandleBuilder):
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, InsideDetail] = {}

    if raw_df is None or raw_df.empty:
        return hits, tickers[:], details

    for t in tickers:
        try:
            candles = build(raw_df, t)
            if candles is None or candles.empty or len(candles) < 2:
                failures.append(t)
                continue

            candles = candles.dropna(subset=["High", "Low"]).sort_index()
            prev = candles.iloc[-2]
            curr = candles.iloc[-1]

            prev_label = str(candles.index[-2])[:10]
            curr_label = str(candles.index[-1])[:10]

            ph, pl = float(prev["High"]), float(prev["Low"])
            ch, cl = float(curr["High"]), float(curr["Low"])

            details[t] = (prev_label, curr_label, ph, pl, ch, cl)

            if (ch <= ph) and (cl >= pl):
                hits.append(t)

        except Exception:
            failures.append(t)

    return hits, failures, details


def format_inside(
    title: str,
    hits: List[str],
    failures: List[str],
    details: Dict[str, InsideDetail],
    prev_tag: str,
    curr_tag: str,
) -> List[str]:
    lines: List[str] = [f"**{title}**"]

    if hits:
        for t in hits:
            prev_date, curr_date, ph, pl, ch, cl = details[t]
            lines.append(
                f"- **Inside on `{t}`**  \n"
                f"  `{prev_date}` {prev_tag}: `{ph:.5f}` / `{pl:.5f}`  \n"
                f"  `{curr_date}` {curr_tag}: `{ch:.5f}` / `{cl:.5f}`"
            )
    else:
        lines.append("- None")

    if failures:
        lines += ["", f"**{title} data unavailable:**"]
        for t in sorted(set(failures)):
            lines.append(f"- `{t}`")

    return lines
