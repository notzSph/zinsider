from __future__ import annotations

import requests

DISCORD_API_BASE = "https://discord.com/api/v10"


def _split_for_discord(message: str, limit: int = 1900):
    """
    Split message into <=limit chunks, preferring to split on list-item boundaries.
    Priority: last '\\n-' within window, then last '-', then last '\\n', else hard cut.
    """
    s = message
    i = 0
    n = len(s)

    while i < n:
        end = min(i + limit, n)
        if end == n:
            yield s[i:end].rstrip()
            break

        window = s[i:end]

        cut = window.rfind("\n-")  # best: keep list items intact
        if cut <= 0:
            cut = window.rfind("-")  # fallback: any dash
        if cut <= 0:
            cut = window.rfind("\n")  # fallback: newline
        if cut <= 0:
            cut = len(window)  # last resort: hard cut

        yield s[i : i + cut].rstrip()

        i = i + cut
        # skip whitespace/newlines so next chunk doesn't start with blank lines
        while i < n and s[i] in " \t\r\n":
            i += 1


def send_discord_message(
    message: str,
    bot_token: str,
    channel_id: str,
    dry_run: bool = False,
    role_id: str = "",
    allow_role_ping: bool = False,
) -> None:
    if dry_run:
        print(message)
        return
    if not bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    if not channel_id:
        raise RuntimeError("Discord channel ID is not set")

    message = (message or "").strip()
    if not message:
        return  # or: message = "No findings today."

    # Deterministic role mention behavior
    allowed_mentions = {"parse": []}
    if allow_role_ping and role_id:
        allowed_mentions = {"roles": [role_id]}

    def post(content: str) -> None:
        payload = {"content": content, "allowed_mentions": allowed_mentions}
        headers = {"Authorization": f"Bot {bot_token}"}
        r = requests.post(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"Discord bot message failed {r.status_code}: {r.text}\n"
                f"len(content)={len(content)}"
            )
        r.raise_for_status()

    # Discord content limit is 2000 characters
    if len(message) > 2000:
        for part in _split_for_discord(message, limit=1900):
            post(part)
        return

    post(message)
