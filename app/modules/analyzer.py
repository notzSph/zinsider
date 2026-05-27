from __future__ import annotations

from typing import Iterable

import pandas as pd

from app.modules.inside import detect_inside
from app.modules.retest import detect_rounded_retests
from app.modules.signals import candles_week_from_day_direct
from app.modules.zebra import detect_zebra


def _signal(
    ticker: str,
    model: str,
    timeframe: str,
    signal_date: str,
    direction: str = "",
    computed: dict | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "model": model,
        "timeframe": timeframe,
        "signal_date": signal_date,
        "direction": direction,
        "computed": computed or {},
    }


def analyze_daily_map(df_map: dict[str, pd.DataFrame], tickers: Iterable[str]) -> tuple[list[dict], list[str]]:
    tickers = list(tickers)
    signals: list[dict] = []
    failures: list[str] = []

    day_hits, day_fail, day_det = detect_inside(
        df_map,
        tickers,
        build=lambda raw, t: raw.get(t),
    )
    failures.extend(day_fail)
    for ticker in day_hits:
        prev_date, curr_date, prev_high, prev_low, curr_high, curr_low = day_det[ticker]
        signals.append(
            _signal(
                ticker,
                "ID",
                "D",
                curr_date,
                computed={
                    "previous_date": prev_date,
                    "previous_high": prev_high,
                    "previous_low": prev_low,
                    "current_high": curr_high,
                    "current_low": curr_low,
                },
            )
        )

    week_hits, _week_fail, week_det = detect_inside(
        df_map,
        tickers,
        build=lambda raw, t: candles_week_from_day_direct(raw.get(t), min_days=3),
    )
    # Weekly/shape models need more history than ID. Missing those inputs should
    # not make the whole ticker look broken in the digest.
    for ticker in week_hits:
        prev_date, curr_date, prev_high, prev_low, curr_high, curr_low = week_det[ticker]
        signals.append(
            _signal(
                ticker,
                "IW",
                "W",
                curr_date,
                computed={
                    "previous_date": prev_date,
                    "previous_high": prev_high,
                    "previous_low": prev_low,
                    "current_high": curr_high,
                    "current_low": curr_low,
                },
            )
        )

    rr_hits, _rr_fail, rr_det = detect_rounded_retests(df_map, tickers)
    for ticker in rr_hits:
        direction, d1, d2, d3, h1, l1, c2, level3 = rr_det[ticker]
        signals.append(
            _signal(
                ticker,
                "+RR",
                "D",
                d3,
                direction,
                {
                    "d1": d1,
                    "d2": d2,
                    "d3": d3,
                    "d1_high": h1,
                    "d1_low": l1,
                    "d2_close": c2,
                    "d3_level": level3,
                },
            )
        )

    zebra_day_hits, _zebra_day_fail, zebra_day_det = detect_zebra(
        df_map,
        tickers,
        build=lambda raw, t: raw.get(t),
    )
    for ticker in zebra_day_hits:
        direction, curr_date, matched_pattern = zebra_day_det[ticker]
        signals.append(
            _signal(
                ticker,
                "Zebra",
                "D",
                curr_date,
                direction,
                {"pattern": matched_pattern},
            )
        )

    zebra_week_hits, _zebra_week_fail, zebra_week_det = detect_zebra(
        df_map,
        tickers,
        build=lambda raw, t: candles_week_from_day_direct(raw.get(t), min_days=3),
    )
    for ticker in zebra_week_hits:
        direction, curr_date, matched_pattern = zebra_week_det[ticker]
        signals.append(
            _signal(
                ticker,
                "Zebra",
                "W",
                curr_date,
                direction,
                {"pattern": matched_pattern},
            )
        )

    return signals, sorted(set(failures))
