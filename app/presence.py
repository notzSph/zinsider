from __future__ import annotations

import logging
import threading

import discord

log = logging.getLogger(__name__)

STATUS_MAP = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "busy": discord.Status.dnd,
    "invisible": discord.Status.invisible,
}


class PresenceClient(discord.Client):
    def __init__(self, status: str, activity: str):
        intents = discord.Intents.none()
        super().__init__(intents=intents)
        self._status = STATUS_MAP.get(status, discord.Status.idle)
        self._activity = activity
        self._presence_applied = False

    async def on_ready(self) -> None:
        if self._presence_applied:
            log.info("Discord presence reconnected for %s", self.user)
            return

        await self.change_presence(
            status=self._status,
            activity=discord.CustomActivity(name=self._activity),
        )
        self._presence_applied = True
        log.info("Discord presence set for %s", self.user)


def run_presence(token: str, status: str, activity: str) -> None:
    client = PresenceClient(status=status, activity=activity)
    try:
        client.run(token, log_handler=None)
    except Exception:
        log.exception("Discord presence client stopped unexpectedly")


def start_presence_thread(settings: dict) -> threading.Thread | None:
    if not settings.get("discord_presence_enabled", True):
        return None

    token = settings.get("discord_bot_token", "")
    if not token:
        log.info("DISCORD_BOT_TOKEN not set; presence disabled")
        return None

    thread = threading.Thread(
        target=run_presence,
        args=(
            token,
            settings.get("discord_presence_status", "idle"),
            settings.get("discord_presence_activity", "zInsider"),
        ),
        name="discord-presence",
        daemon=True,
    )
    thread.start()
    return thread
