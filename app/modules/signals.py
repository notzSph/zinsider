from __future__ import annotations

from typing import Dict, List, Optional, Tuple

InsideDayDetail = Tuple[str, str, float, float, float, float]


def extract_last_two_daily_bars(high_s, low_s) -> Optional[InsideDayDetail]:
    """
    Extract last two daily bars (high/low) from two aligned series.
    """
    high_s = high_s.dropna()
    low_s = low_s.dropna()

    if len(high_s) < 2 or len(low_s) < 2:
        return None

    idx = high_s.index.intersection(low_s.index)
    if len(idx) < 2:
        return None

    high_s = high_s.loc[idx]
    low_s = low_s.loc[idx]

    prev_i, curr_i = -2, -1
    prev_date = idx[prev_i].strftime("%Y-%m-%d")
    curr_date = idx[curr_i].strftime("%Y-%m-%d")

    return (
        prev_date,
        curr_date,
        float(high_s.iloc[prev_i]),
        float(low_s.iloc[prev_i]),
        float(high_s.iloc[curr_i]),
        float(low_s.iloc[curr_i]),
    )


def is_inside_day(prev_high: float, prev_low: float, curr_high: float, curr_low: float) -> bool:
    """
    True if current day's range is fully inside the previous day's range.
    """
    return (curr_high <= prev_high) and (curr_low >= prev_low)


def detect_inside_days(df, tickers: List[str]):
    """
    Evaluate inside-day condition for each ticker.

    Returns:
      - hits: list of tickers with inside day
      - failures: list of tickers that could not be evaluated
      - details: dict[ticker] -> (prev_date, curr_date, prev_high, prev_low, curr_high, curr_low)
    """
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, InsideDayDetail] = {}

    if df is None or df.empty:
        return hits, tickers[:], details

    multi = getattr(df.columns, "nlevels", 1) > 1

    for t in tickers:
        try:
            if multi:
                if "High" not in df.columns.levels[0] or "Low" not in df.columns.levels[0]:
                    failures.append(t)
                    continue
                if t not in df["High"].columns or t not in df["Low"].columns:
                    failures.append(t)
                    continue

                high_s = df["High"][t]
                low_s = df["Low"][t]
            else:
                high_s = df["High"]
                low_s = df["Low"]

            extracted = extract_last_two_daily_bars(high_s, low_s)
            if not extracted:
                failures.append(t)
                continue

            details[t] = extracted
            _, _, ph, pl, ch, cl = extracted

            if is_inside_day(ph, pl, ch, cl):
                hits.append(t)

        except Exception:
            failures.append(t)

    return hits, failures, details
