from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Provider ticker -> canonical zInsider display ticker. This is the single
# source of truth for market symbols; render.py consumes it rather than keeping
# a second map.
TICKER_DISPLAY = {
    "ES=F": "ES",
    "NQ=F": "NQ",
    "YM=F": "YM",
    "RTY=F": "RTY",
    "GC=F": "GC",
    "SI=F": "SI",
    "HG=F": "HG",
    "HO=F": "HO",
    "PL=F": "PL",
    "PA=F": "PA",
    "CL=F": "CL",
    "BZ=F": "BRN",
    "NG=F": "NG",
    "RB=F": "RB",
    "ZB=F": "US",
    "ZN=F": "ZN",
    "ZC=F": "ZC",
    "ZW=F": "ZW",
    "ZS=F": "ZS",
    "ZM=F": "ZM",
    "ZL=F": "ZL",
    "CC=F": "CC",
    "CT=F": "CT",
    "KC=F": "KC",
    "HE=F": "HE",
    "LE=F": "LE",
}

# TradingView may send the compact symbols used by older zInsider alerts. They
# are input aliases only; every stored/rendered FX ticker uses the canonical
# symbol below. Yahoo-style ``=X`` symbols are deliberately not supported.
TRADINGVIEW_TICKER_ALIASES = {
    "NU": "NZD",
    "UCHF": "CHF",
    "UCAD": "CAD",
}

TRADINGVIEW_FX_TICKERS = frozenset(
    {"EU", "GU", "EG", "AU", "NZD", "CHF", "CAD", "UJ", "EJ", "GJ", "DXY"}
)

# Canonical zInsider ticker -> live Discord emoji. Provider-specific keys are
# forbidden here; use TICKER_DISPLAY above to normalise first.
TICKER_EMOJIS = {
    "EU": "<:eu:1531340162997424208>",
    "EG": "<:exy:1294755823893086279>",
    "EJ": "<:exy:1294755823893086279>",
    "DXY": "<:dxy:1294755822290731019>",
    "GU": "<:bxy:1294755820864667688>",
    "GJ": "<:bxy:1294755820864667688>",
    "CAD": "<:cxy:1535631926809989120>",
    "CHF": "<:sxy:1535238586184503336>",
    "AU": "<:axy:1535238529255350345>",
    "UJ": "<:jxy:1531572491439571278>",
    "NZD": "<:zxy:1535630504483754055>",
    "ES": "<:es:1294720279192535090>",
    "NQ": "<:nq:1531340173395234856>",
    "YM": "<:ym:1294743731643351212>",
    "RTY": "<:rty:1531340177190948934>",
    "FDAX": "<:dax:1294743837092352022>",
    "FESX": "<:fesx:1531340165195235328>",
    "FIB": "<:fib:1531340167569477662>",
    "GC": "<:gold:1294720270199951444>",
    "HG": "<:hg:1535238536855556196>",
    "HO": "<:ho:1541470211973185636>",
    "PL": "<:pl:1541470215139762237>",
    "PA": "<:pa:1541470213583671408>",
    "CL": "<:crudeoil:1294743881434533898>",
    "BRN": "<:crudeoil:1294743881434533898>",
    "NG": "<:ng:1531340171214196786>",
    "SI": "<:si:1531340179108008177>",
    "RB": "<:rb:1535238584372690944>",
    "US": "<:us:1531341929311244419>",
    "ZN": "<:us:1531341929311244419>",
    "ZC": "<:zc:1535238587497451540>",
    "ZW": "<:zw:1535238594040696932>",
    "ZS": "<:zs:1535238592140542034>",
    "ZM": "<:zm:1535238589930274840>",
    "ZL": "<:zl:1535238588797685801>",
    "CC": "<:cc:1535238531021013032>",
    "CT": "<:ct:1535238533269422080>",
    "KC": "<:kc:1535238538705244271>",
    "HE": "<:he:1535238535399874652>",
    "LE": "<:le:1535238582590115870>",
    "FGBL": "<:bxy:1294755820864667688>",
}

# Canonical zInsider ticker -> exchange minimum price increment. Prices are
# snapped to these increments before rendering, keeping output honest (e.g.
# YM trades in whole points, not five-decimal fantasy prices).
TICKER_TICK_SIZES = {
    # FX and dollar index
    "EU": "0.00001", "EG": "0.00001", "EJ": "0.001", "GU": "0.00001",
    "GJ": "0.001", "CAD": "0.00001", "CHF": "0.00001", "AU": "0.00001",
    "UJ": "0.001", "NZD": "0.00001", "DXY": "0.005",
    # Equity indices
    "ES": "0.25", "NQ": "0.25", "YM": "1", "RTY": "0.10",
    "FDAX": "0.50", "FESX": "0.50", "FIB": "5",
    # Metals and energy
    "GC": "0.10", "SI": "0.005", "HG": "0.0005", "HO": "0.0001", "PL": "0.10",
    "PA": "0.10", "CL": "0.01", "BRN": "0.01", "NG": "0.001",
    "RB": "0.0001",
    # Rates, agriculture and livestock
    "US": "0.03125", "ZN": "0.015625", "FGBL": "0.01",
    "ZC": "0.25", "ZW": "0.25", "ZS": "0.25", "ZM": "0.10",
    "ZL": "0.01", "CC": "1", "CT": "0.01", "KC": "0.05",
    "HE": "0.025", "LE": "0.025",
}

DEFAULT_FUTURES = [
    "ES=F",
    "NQ=F",
    "YM=F",
    "RTY=F",
    "GC=F",
    "SI=F",
    "HG=F",
    "HO=F",
    "PL=F",
    "PA=F",
    "CL=F",
    "BZ=F",
    "NG=F",
    "RB=F",
]

def get_futures(settings: dict | None = None) -> list[str]:
    if settings and settings.get("futures_tickers"):
        return list(settings["futures_tickers"])
    return DEFAULT_FUTURES[:]


def normalize_ticker(ticker: str) -> str:
    """Canonicalise a TradingView symbol without accepting Yahoo FX aliases."""
    t = ticker.strip().upper()
    if not t:
        return t
    if ":" in t:
        t = t.rsplit(":", 1)[-1]
    return TRADINGVIEW_TICKER_ALIASES.get(t, t)


def format_price(ticker: str, value: object) -> str | None:
    """Snap a price to its canonical market tick and render useful digits only."""
    normalized = normalize_ticker(ticker)
    canonical = TICKER_DISPLAY.get(normalized, normalized)
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    tick_text = TICKER_TICK_SIZES.get(canonical)
    if tick_text is None:
        return f"{price:.5f}"

    tick = Decimal(tick_text)
    snapped = (price / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
    decimals = max(0, -tick.as_tuple().exponent)
    return f"{snapped:.{decimals}f}"
