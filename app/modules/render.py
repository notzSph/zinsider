from __future__ import annotations

from collections import defaultdict
from datetime import datetime


STREAM_THREADS = {
    "digest": "discord_digest_thread_id",
    "ID": "discord_id_thread_id",
    "IW": "discord_iw_thread_id",
    "+RR": "discord_rr_thread_id",
    "Zebra": "discord_zebra_thread_id",
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


def render_digest(title: str, signals: list[dict], failures: list[str]) -> str:
    grouped = _group(signals)
    lines = [title, ""]

    if not signals:
        lines.append("No active setups.")
    else:
        for model in ("ID", "IW", "+RR", "Zebra"):
            items = grouped.get(model, [])
            if not items:
                continue
            compact = ", ".join(_fmt_signal(sig) for sig in sorted(items, key=lambda x: (x["ticker"], x["timeframe"])))
            lines.append(f"**EU {model}**")
            lines.append(compact)
            lines.append("")

    if failures:
        lines.append("**Data issues**")
        lines.append(", ".join(f"`{ticker}`" for ticker in failures[:20]))
        if len(failures) > 20:
            lines.append(f"...and {len(failures) - 20} more")

    return "\n".join(lines).strip()


def _num(value) -> str | None:
    try:
        return f"{float(value):.5f}"
    except (TypeError, ValueError):
        return None


def render_stream(model: str, signals: list[dict], source: str) -> str:
    items = [sig for sig in signals if sig["model"] == model]
    if not items:
        return ""

    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = [f"**{today} EU {model}**", f"Source: `{source}`", ""]

    for sig in sorted(items, key=lambda x: (x["ticker"], x["timeframe"], x.get("direction", ""))):
        computed = sig.get("computed", {})
        direction = f" {sig['direction']}" if sig.get("direction") else ""
        lines.append(f"- `{sig['ticker']}` {sig['timeframe']}{direction} ({sig['signal_date']})")

        if model in ("ID", "IW"):
            prev_high = _num(computed.get("previous_high"))
            prev_low = _num(computed.get("previous_low"))
            curr_high = _num(computed.get("current_high"))
            curr_low = _num(computed.get("current_low"))
            if prev_high and prev_low and curr_high and curr_low:
                lines.append(f"  prev `{prev_high}/{prev_low}` curr `{curr_high}/{curr_low}`")
        elif model == "+RR":
            d1_high = _num(computed.get("d1_high"))
            d1_low = _num(computed.get("d1_low"))
            if d1_high and d1_low:
                lines.append(f"  D1 `{computed.get('d1')}` H/L `{d1_high}/{d1_low}`")
        elif model == "Zebra":
            if computed.get("pattern"):
                lines.append(f"  pattern `{computed.get('pattern')}`")

    return "\n".join(lines)
