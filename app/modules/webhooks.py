from __future__ import annotations

import requests


def send_discord_message(message: str, webhook_url: str, dry_run: bool = False) -> None:
    """
    Send a message to a Discord webhook.
    """
    if dry_run:
        print(message)
        return
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    r = requests.post(webhook_url, json={"content": message}, timeout=15)
    r.raise_for_status()
