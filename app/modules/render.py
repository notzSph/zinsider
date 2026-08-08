from __future__ import annotations

from collections import defaultdict

from app.modules.assets import TICKER_DISPLAY, TICKER_EMOJIS, format_price

STREAM_THREADS = {
    "daily_digest": "discord_daily_digest_thread_id",
    "weekly_digest": "discord_weekly_digest_thread_id",
    "ID": "discord_id_thread_id",
    "IW": "discord_iw_thread_id",
    "+RR": "discord_daily_rr_plus_thread_id",
    "-RR": "discord_daily_rr_minus_thread_id",
    "+RR Weekly": "discord_weekly_rr_plus_thread_id",
    "-RR Weekly": "discord_weekly_rr_minus_thread_id",
    "Bullish Zebra": "discord_daily_zebra_thread_id",
    "Bearish Zebra": "discord_daily_zebra_thread_id",
    "Bullish Weekly Zebra": "discord_weekly_zebra_thread_id",
    "Bearish Weekly Zebra": "discord_weekly_zebra_thread_id",
}

DAILY_MODEL_ORDER = ("ID", "+RR", "-RR", "Bullish Zebra", "Bearish Zebra")
WEEKLY_MODEL_ORDER = ("IW", "+RR Weekly", "-RR Weekly", "Bullish Weekly Zebra", "Bearish Weekly Zebra")
MODEL_ORDER = DAILY_MODEL_ORDER + WEEKLY_MODEL_ORDER
ZEBRA_MODELS = frozenset({"Bullish Zebra", "Bearish Zebra", "Bullish Weekly Zebra", "Bearish Weekly Zebra"})
RR_MODELS = frozenset({"+RR", "-RR", "+RR Weekly", "-RR Weekly"})

MODEL_TITLES = {
    "ID": "Inside Day Failure",
    "IW": "Inside Week Failure",
    "+RR": "Bullish Rounded Retest",
    "-RR": "Bearish Rounded Retest",
    "+RR Weekly": "Bullish Weekly Rounded Retest",
    "-RR Weekly": "Bearish Weekly Rounded Retest",
    "Bullish Zebra": "Bullish Zebra",
    "Bearish Zebra": "Bearish Zebra",
    "Bullish Weekly Zebra": "Bullish Weekly Zebra",
    "Bearish Weekly Zebra": "Bearish Weekly Zebra",
}

MODEL_SECTION_TITLES = {
    "ID": "Inside Day Failures",
    "IW": "Inside Week Failures",
    "+RR": "Bullish Rounded Retests",
    "-RR": "Bearish Rounded Retests",
    "+RR Weekly": "Bullish Weekly Rounded Retests",
    "-RR Weekly": "Bearish Weekly Rounded Retests",
    "Bullish Zebra": "Bullish Zebra",
    "Bearish Zebra": "Bearish Zebra",
    "Bullish Weekly Zebra": "Bullish Weekly Zebra",
    "Bearish Weekly Zebra": "Bearish Weekly Zebra",
}


def _group(signals: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for sig in signals:
        grouped[sig["model"]].append(sig)
    return grouped


def _fmt_signal(sig: dict) -> str:
    bits = [sig["ticker"]]
    if sig.get("direction"):
        bits.append(sig["direction"])
    bits.append(sig["timeframe"])
    return " ".join(bits)


def _display_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    return TICKER_DISPLAY.get(normalized, normalized)


def _ticker_emoji(display_ticker: str) -> str:
    return TICKER_EMOJIS.get(display_ticker, "")


def _title(sig: dict) -> str:
    display_ticker = _display_ticker(sig["ticker"])
    emoji = _ticker_emoji(display_ticker)
    prefix = f"{emoji} " if emoji else ""
    model_title = MODEL_TITLES.get(sig["model"], sig["model"])
    return f"**{prefix}{display_ticker} - {model_title}**"


def _direction_label(direction: str) -> str:
    normalized = (direction or "").strip().lower()
    if normalized in ("bull", "bullish"):
        return "Bullish"
    if normalized in ("bear", "bearish"):
        return "Bearish"
    return "Inside"


def _key_level(sig: dict) -> str:
    model = sig["model"]
    direction = (sig.get("direction") or "").strip().lower()
    computed = sig.get("computed", {})

    if model in ZEBRA_MODELS:
        expected = "Up" if direction in ("bull", "bullish") else "Down"
        high_label, low_label = ("PDH", "PDL") if sig.get("timeframe") == "D" else ("PWH", "PWL")
        high = _num(sig["ticker"], computed.get("previous_high", computed.get("last_high")))
        low = _num(sig["ticker"], computed.get("previous_low", computed.get("last_low")))
        price = _num(sig["ticker"], computed.get("price"))
        levels = [
            f"{high_label} `{high}`" if high else high_label,
            f"{low_label} `{low}`" if low else low_label,
            f"Price `{price}`" if price else "Price",
            f"Expected continuation: **{expected}**",
        ]
        return " • ".join(levels)

    if model in RR_MODELS:
        if direction in ("bull", "bullish"):
            d1_high = _num(sig["ticker"], computed.get("d1_high"))
            d2_close = _num(sig["ticker"], computed.get("d2_close"))
            d3_low = _num(sig["ticker"], computed.get("d3_level"))
            levels = [
                f"Hammer High `{d1_high}`" if d1_high else "Hammer High",
                f"D2 Close `{d2_close}`" if d2_close else "D2 Close",
                f"D3 Low `{d3_low}`" if d3_low else "D3 Low",
            ]
            return " • ".join(levels)
        if direction in ("bear", "bearish"):
            d1_low = _num(sig["ticker"], computed.get("d1_low"))
            d2_close = _num(sig["ticker"], computed.get("d2_close"))
            d3_high = _num(sig["ticker"], computed.get("d3_level"))
            levels = [
                f"Shooting Star Low `{d1_low}`" if d1_low else "Shooting Star Low",
                f"D2 Close `{d2_close}`" if d2_close else "D2 Close",
                f"D3 High `{d3_high}`" if d3_high else "D3 High",
            ]
            return " • ".join(levels)
        return "Retest Level"

    prev_high = _num(sig["ticker"], computed.get("previous_high"))
    prev_low = _num(sig["ticker"], computed.get("previous_low"))
    if model == "ID":
        high_label, low_label = "PDH", "PDL"
    elif model == "IW":
        high_label, low_label = "PWH", "PWL"
    else:
        high_label, low_label = "Previous High", "Previous Low"
    if prev_high and prev_low:
        return f"{high_label} `{prev_high}` / {low_label} `{prev_low}`"
    return f"{high_label} / {low_label}"


def _render_card(sig: dict) -> list[str]:
    model = sig["model"]
    detail = (
        f"📈 Model: {MODEL_TITLES[model]}"
        if model in ("ID", "IW") or model in ZEBRA_MODELS
        else f"📈 Type: {_direction_label(sig.get('direction', ''))}"
    )
    key_label = "🔑 Key Levels"
    return [_title(sig), detail, f"{key_label}: {_key_level(sig)}"]


def _digest_item(sig: dict) -> list[str]:
    display_ticker = _display_ticker(sig["ticker"])
    emoji = _ticker_emoji(display_ticker)
    prefix = f"{emoji} " if emoji else ""
    direction = _direction_label(sig.get("direction", ""))
    setup = MODEL_TITLES.get(sig["model"], sig["model"])
    context = f" • **{direction}**" if sig["model"] not in ("ID", "IW") else ""
    source = "TradingView" if sig.get("source") == "tradingview" else "Futures scan"
    return [
        f"- {prefix}**{display_ticker}** • `{sig['timeframe']}`{context}",
        f"  - **Key levels:** {_key_level(sig)}",
        f"  - **Model:** {setup}",
        f"  - **Feed:** {source}",
    ]


def render_digest(
    title: str,
    signals: list[dict],
    failures: list[str],
    model_order: tuple[str, ...] = MODEL_ORDER,
) -> str:
    grouped = _group(signals)
    lines = [title, "", f"**Active setups:** {len(signals)}", ""]

    if not signals:
        lines.append("No active setups.")
    else:
        for model in model_order:
            items = grouped.get(model, [])
            if not items:
                continue
            lines.append(f"## {MODEL_SECTION_TITLES[model]}")
            for sig in sorted(items, key=lambda x: (x["ticker"], x["timeframe"], x.get("direction", ""))):
                lines.extend(_digest_item(sig))
            lines.append("")

    if failures:
        lines.append("**Data issues**")
        lines.append(", ".join(f"`{ticker}`" for ticker in failures[:20]))
        if len(failures) > 20:
            lines.append(f"...and {len(failures) - 20} more")

    return "\n".join(lines).strip()


def _num(ticker: str, value: object) -> str | None:
    return format_price(ticker, value)


def render_stream(model: str, signals: list[dict], source: str) -> str:
    items = [sig for sig in signals if sig["model"] == model]
    if not items:
        return ""

    lines: list[str] = []

    for sig in sorted(items, key=lambda x: (x["ticker"], x["timeframe"], x.get("direction", ""))):
        if lines:
            lines.append("")
        lines.extend(_render_card(sig))

    return "\n".join(lines)
