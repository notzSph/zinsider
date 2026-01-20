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
    Return the list of Yahoo tickers to monitor.
    """
    return ASSETS
