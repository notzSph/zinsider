from __future__ import annotations


ASSETS = [
    "EURUSD=X",
    "GBPUSD=X",
    "AUDUSD=X",
    "NZDUSD=X",
    "USDCAD=X",
    "USDCHF=X",
    "USDJPY=X",
    "EURAUD=X",
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X",
    "AUDJPY=X",
    "AUDNZD=X",
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
    Return the list of Yahoo-style tickers to monitor.
    """
    return ASSETS


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