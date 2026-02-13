from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple

import pandas as pd

InsideDayDetail = Tuple[str, str, float, float, float, float]
# (prev_session_end_date, curr_session_end_date, prev_high, prev_low, curr_high, curr_low)


def _to_utc_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
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

    sessions.index = pd.to_datetime(sessions.index).tz_localize(tz)
    sessions["session_end"] = sessions.index.normalize() + pd.Timedelta(hours=17)

    now_ny = datetime.now(tz)
    sessions = sessions[sessions["session_end"] <= now_ny]

    return sessions


def detect_inside_days_eth(df_hourly, tickers: List[str], ny_timezone: str):
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


# -----------------------------
# Candle builders for generic inside day/week
# -----------------------------

def _extract_ohlc(df_hourly: pd.DataFrame, t: str):
    multi = getattr(df_hourly.columns, "nlevels", 1) > 1
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
    return o.loc[idx], h.loc[idx], l.loc[idx], c.loc[idx]


def candles_day_eth(df_hourly: pd.DataFrame, t: str, ny_timezone: str) -> pd.DataFrame:
    o, h, l, c = _extract_ohlc(df_hourly, t)
    sessions = _build_eth_sessions_18_17(o, h, l, c, ny_timezone)
    if sessions is None or sessions.empty:
        return pd.DataFrame()

    candles = sessions[["Open", "High", "Low", "Close"]].copy()
    candles.index = sessions["session_end"].dt.strftime("%Y-%m-%d")
    return candles


def candles_week_from_day(df_hourly: pd.DataFrame, t: str, ny_timezone: str, min_days: int = 3) -> pd.DataFrame:
    daily = candles_day_eth(df_hourly, t, ny_timezone)
    if daily is None or daily.empty or len(daily) < 5:
        return pd.DataFrame()

    idx = pd.to_datetime(daily.index)
    d = daily.copy()
    d["_d"] = idx

    wk = d["_d"].dt.to_period("W-FRI")
    g = d.groupby(wk, sort=True)

    weekly = pd.DataFrame(
        {
            "Open": g["Open"].first(),
            "High": g["High"].max(),
            "Low": g["Low"].min(),
            "Close": g["Close"].last(),
            "count": g["Close"].count(),
        }
    )

    weekly = weekly[weekly["count"] >= min_days].drop(columns=["count"])
    weekly.index = [str(p.end_time.date()) for p in weekly.index]
    return weekly
