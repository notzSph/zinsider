from __future__ import annotations


FX_ALIASES = {
    "EU": "EURUSD=X",
    "GU": "GBPUSD=X",
    "EG": "EURGBP=X",
    "AU": "AUDUSD=X",
    "NU": "NZDUSD=X",
    "UCHF": "USDCHF=X",
    "UCAD": "USDCAD=X",
    "UJ": "USDJPY=X",
    "EJ": "EURJPY=X",
    "GJ": "GBPJPY=X",
}

DEFAULT_FUTURES = [
    "ES=F",
    "NQ=F",
    "YM=F",
    "RTY=F",
    "GC=F",
    "SI=F",
    "HG=F",
    "PL=F",
    "PA=F",
    "CL=F",
    "BZ=F",
    "NG=F",
    "RB=F",
]


def get_assets() -> list[str]:
    """
    Return the complete default universe.
    """
    return list(FX_ALIASES.values()) + DEFAULT_FUTURES[:]


def get_futures(settings: dict | None = None) -> list[str]:
    if settings and settings.get("futures_tickers"):
        return list(settings["futures_tickers"])
    return DEFAULT_FUTURES[:]


def normalize_ticker(ticker: str) -> str:
    t = ticker.strip().upper()
    if not t:
        return t
    if ":" in t:
        t = t.rsplit(":", 1)[-1]
    if t in FX_ALIASES:
        return FX_ALIASES[t]
    if len(t) == 6 and t.isalpha():
        return f"{t}=X"
    return t


def is_fx_ticker(ticker: str) -> bool:
    """
    FX tickers are expected in Yahoo style, e.g. EURUSD=X
    """
    t = ticker.strip().upper()
    return t.endswith("=X") and len(t[:-2]) == 6 and t[:-2].isalpha()


def split_assets(tickers: list[str]) -> tuple[list[str], list[str]]:
    """
    Returns:
        fx_tickers, other_tickers
    """
    fx = [t for t in tickers if is_fx_ticker(t)]
    other = [t for t in tickers if not is_fx_ticker(t)]
    return fx, other
