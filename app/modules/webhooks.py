from __future__ import annotations

import requests


def send_discord_message(
    message: str,
    webhook_url: str,
    dry_run: bool = False,
    role_id: str = "",
    allow_role_ping: bool = False,
) -> None:
    if dry_run:
        print(message)
        return
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    payload = {"content": message}

    # Deterministic role mention behavior
    if allow_role_ping and role_id:
        payload["allowed_mentions"] = {"roles": [role_id]}
    else:
        payload["allowed_mentions"] = {"parse": []}

    r = requests.post(webhook_url, json=payload, timeout=15)
    r.raise_for_status()
