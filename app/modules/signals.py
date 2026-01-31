from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple

import pandas as pd

InsideDayDetail = Tuple[str, str, float, float, float, float]
# (prev_session_end_date, curr_session_end_date, prev_high, prev_low, curr_high, curr_low)


def _to_utc_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    # yfinance can return tz-naive or tz-aware indexes depending on symbol
    if idx.tz is None:
        return idx.tz_localize("UTC")
    return idx.tz_convert("UTC")


def _build_eth_sessions_18_17(
    o: pd.Series,
    h: pd.Series,
    l: pd.Series,
    c: pd.Series,
    ny_timezone: str,
) -> pd.DataFrame:
    """
    Build ETH session candles using:
      - session open: 18:00 NY
      - session close: 17:00 NY next day
      - exclude maintenance: 17:00–18:00 NY

    We label each session by its session close date (the date of the 17:00 NY close).
    """
    tz = ZoneInfo(ny_timezone)

    idx_ny = _to_utc_index(o.index).tz_convert(tz)
    df = pd.DataFrame(
        {"Open": o.values, "High": h.values, "Low": l.values, "Close": c.values},
        index=idx_ny,
    ).dropna()

    if df.empty:
        return df

    # Drop maintenance hour 17:00–17:59 NY
    df = df[df.index.hour != 17]
    if df.empty:
        return df

    # Session close date assignment:
    # - Bars at 18:00..23:59 belong to session closing the NEXT calendar day at 17:00
    # - Bars at 00:00..16:59 belong to session closing SAME calendar day at 17:00
    end_dates = pd.Series(df.index.date, index=df.index)
    evening = df.index.hour >= 18
    end_dates.loc[evening] = (df.index[evening] + pd.Timedelta(days=1)).date
    df["session_end_date"] = end_dates.values

    g = df.groupby("session_end_date", sort=True)

    sessions = pd.DataFrame(
        {
            "Open": g["Open"].first(),
            "High": g["High"].max(),
            "Low": g["Low"].min(),
            "Close": g["Close"].last(),
        }
    )

    # Build a concrete close timestamp for filtering completed sessions
    sessions.index = pd.to_datetime(sessions.index).tz_localize(tz)
    sessions["session_end"] = sessions.index.normalize() + pd.Timedelta(hours=17)

    # Keep only completed sessions (ended at/before now)
    now_ny = datetime.now(tz)
    sessions = sessions[sessions["session_end"] <= now_ny]

    return sessions


def detect_inside_days_eth(df_hourly, tickers: List[str], ny_timezone: str):
    """
    Inside day computed on last two completed ETH sessions (18:00->17:00 NY).
    """
    hits: List[str] = []
    failures: List[str] = []
    details: Dict[str, InsideDayDetail] = {}

    if df_hourly is None or df_hourly.empty:
        return hits, tickers[:], details

    multi = getattr(df_hourly.columns, "nlevels", 1) > 1

    for t in tickers:
        try:
            if multi:
                for col in ("Open", "High", "Low", "Close"):
                    if col not in df_hourly.columns.levels[0] or t not in df_hourly[col].columns:
                        raise KeyError(f"missing {col} for {t}")
                o = df_hourly["Open"][t].dropna()
                h = df_hourly["High"][t].dropna()
                l = df_hourly["Low"][t].dropna()
                c = df_hourly["Close"][t].dropna()
            else:
                o = df_hourly["Open"].dropna()
                h = df_hourly["High"].dropna()
                l = df_hourly["Low"].dropna()
                c = df_hourly["Close"].dropna()

            idx = o.index.intersection(h.index).intersection(l.index).intersection(c.index)
            if len(idx) < 30:
                failures.append(t)
                continue

            o, h, l, c = o.loc[idx], h.loc[idx], l.loc[idx], c.loc[idx]
            sessions = _build_eth_sessions_18_17(o, h, l, c, ny_timezone)

            if len(sessions) < 2:
                failures.append(t)
                continue

            prev = sessions.iloc[-2]
            curr = sessions.iloc[-1]

            prev_end = prev["session_end"].strftime("%Y-%m-%d")
            curr_end = curr["session_end"].strftime("%Y-%m-%d")

            ph, pl = float(prev["High"]), float(prev["Low"])
            ch, cl = float(curr["High"]), float(curr["Low"])

            details[t] = (prev_end, curr_end, ph, pl, ch, cl)

            if (ch <= ph) and (cl >= pl):
                hits.append(t)

        except Exception:
            failures.append(t)

    return hits, failures, details
