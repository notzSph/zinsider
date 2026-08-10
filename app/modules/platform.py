"""Delivery of zInsider digest snapshots to the zTrading platform."""

from __future__ import annotations

from datetime import datetime, timezone

import requests


def send_digest(settings: dict, payload: dict) -> None:
    if not settings["platform_digest_enabled"]:
        return
    base_url = settings["platform_api_url"]
    token = settings["platform_ingest_token"]
    if not base_url or not token:
        raise RuntimeError("Platform digest delivery is enabled without API URL/token")
    response = requests.post(
        f"{base_url}/api/v1/insider/digests",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()


def digest_payload(period: str, run_key: str, text: str, signals: list[dict], failures: list[str], bars: int) -> dict:
    return {
        "period": period,
        "run_key": run_key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "digest_text": text,
        "signals": signals,
        "failures": failures,
        "bars_count": bars,
        "signals_count": len(signals),
    }
