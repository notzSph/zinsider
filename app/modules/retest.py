from __future__ import annotations

from typing import Dict, List, Optional, Tuple


RoundedDetail = Tuple[str, str, str, float, float, float, float]
# (d1_date, d2_date, d3_date, d1_high, d1_low, d2_close, d3_low)


def is_hammer(open_: float, high: float, low: float, close: float) -> bool:
    """
    Hammer heuristic (stable defaults):
      - small body (<= 30% of range)
      - long lower wick (>= 2x body)
      - upper wick not dominant (<= 1x body)
      - body in top 40% of range
    """
    rng = high - low
    if rng <= 0:
        return False

    body = abs(close - open_)
    # avoid divide-by-zero while keeping doji-ish bodies "small"
    body = max(body, rng * 0.01)

    upper = high - max(open_, close)
    lower = min(open_, close) - low

    if (body / rng) > 0.30:
        return False
    if lower < 2.0 * body:
        return False
    if upper > 1.0 * body:
        return False

    body_top = max(open_, close)
    if body_top < (low + 0.60 * rng):
        return False

    return True


def _extract_last_three(
    o_s, h_s, l_s, c_s
) -> Optional[Tuple[str, str, str, float, float, float, float, float, float, float, float, float]]:
    """
    Returns:
      d1_date, d2_date, d3_date,
      d1_o, d1_h, d1_l, d1_c,
      d2_o, d2_h, d2_l, d2_c,
      d3_o, d3_h, d3_l, d3_c
    """
    o_s = o_s.dropna()
    h_s = h_s.dropna()
    l_s = l_s.dropna()
    c_s = c_s.dropna()

    idx = o_s.index.intersection(h_s.index).intersection(l_s.index).intersection(c_s.index)
    if len(idx) < 3:
        return None

    o_s = o_s.loc[idx]
    h_s = h_s.loc[idx]
    l_s = l_s.loc[idx]
    c_s = c_s.loc[idx]

    d1_i, d2_i, d3_i = -3, -2, -1
    d1_date = idx[d1_i].strftime("%Y-%m-%d")
    d2_date = idx[d2_i].strftime("%Y-%m-%d")
    d3_date = idx[d3_i].strftime("%Y-%m-%d")

    return (
        d1_date, d2_date, d3_date,
        float(o_s.iloc[d1_i]), float(h_s.iloc[d1_i]), float(l_s.iloc[d1_i]), float(c_s.iloc[d1_i]),
        float(o_s.iloc[d2_i]), float(h_s.iloc[d2_i]), float(l_s.iloc[d2_i]), float(c_s.iloc[d2_i]),
        float(o_s.iloc[d3_i]), float(h_s.iloc[d3_i]), float(l_s.iloc[d3_i]), float(c_s.iloc[d3_i]),
    )


def detect_rounded_retests(df, tickers: List[str]):
    """
    Rounded retest (bullish) per your 3-day spec:

    1) Day 1 (D-2) is hammer
    2) Day 2 (D-1) bullish engulf condition: Close > High of Day 1
    3) Day 3 (D0) low > High of Day 1 (no touch)

    Returns:
      hits: tickers meeting conditions
      failures: tickers we couldn't evaluate
      details: dict[ticker] -> RoundedDetail
    """
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, RoundedDetail] = {}

    if df is None or df.empty:
        return hits, tickers[:], details

    multi = getattr(df.columns, "nlevels", 1) > 1

    for t in tickers:
        try:
            if multi:
                required = ("Open", "High", "Low", "Close")
                if any(r not in df.columns.levels[0] for r in required):
                    failures.append(t)
                    continue
                if any(t not in df[r].columns for r in required):
                    failures.append(t)
                    continue

                o_s = df["Open"][t]
                h_s = df["High"][t]
                l_s = df["Low"][t]
                c_s = df["Close"][t]
            else:
                o_s = df["Open"]
                h_s = df["High"]
                l_s = df["Low"]
                c_s = df["Close"]

            extracted = _extract_last_three(o_s, h_s, l_s, c_s)
            if not extracted:
                failures.append(t)
                continue

            (
                d1_date, d2_date, d3_date,
                d1_o, d1_h, d1_l, d1_c,
                _d2_o, _d2_h, _d2_l, d2_c,
                _d3_o, _d3_h, d3_l, _d3_c,
            ) = extracted

            # 1) hammer
            if not is_hammer(d1_o, d1_h, d1_l, d1_c):
                continue

            # 2) bullish engulf condition (as defined): close above hammer high
            if not (d2_c > d1_h):
                continue

            # 3) "no touch": today's low strictly above hammer high
            if not (d3_l > d1_h):
                continue

            hits.append(t)
            details[t] = (d1_date, d2_date, d3_date, d1_h, d1_l, d2_c, d3_l)

        except Exception:
            failures.append(t)

    return hits, failures, details
