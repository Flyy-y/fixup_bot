"""fixupx Discord bot.

Watches messages on every guild the bot can see. When a message contains an
``x.com`` link, the bot deletes the original and reposts a fixed copy (with the
host rewritten to ``fixupx.com``) through a channel webhook impersonating the
original author, so Discord renders working Twitter/X embeds.

The Discord token is read exclusively from the ``TOKEN`` environment variable
at runtime and is never logged.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import discord

from .url_transform import has_x_link, transform_text

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("fixupx")

# Name used for the bot-owned webhook created per channel.
WEBHOOK_NAME = "fixupx-bot"

# Heartbeat file touched periodically; the Docker HEALTHCHECK reads its mtime.
HEARTBEAT_FILE = Path(os.environ.get("HEARTBEAT_FILE", "/tmp/fixupx_healthy"))
HEARTBEAT_INTERVAL = 30  # seconds


def _build_content(message: discord.Message) -> str:
    """Build the reposted content: transformed text plus attachment URLs.

    Attachments are handled best-effort by re-injecting their URLs into the
    content (Discord renders them inline) rather than re-uploading bytes.
    """
    parts: list[str] = []
    transformed = transform_text(message.content or "")
    if transformed:
        parts.append(transformed)
    for attachment in message.attachments:
        parts.append(attachment.url)
    return "\n".join(parts).strip()


class FixupClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        super().__init__(intents=intents)

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)
        log.info("Watching %d guild(s)", len(self.guilds))
        self._touch_heartbeat()

    async def setup_hook(self) -> None:
        # Touch the heartbeat immediately so the container is healthy as soon
        # as the event loop is running, then keep it fresh in the background.
        self._touch_heartbeat()
        self.loop.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        while True:
            self._touch_heartbeat()
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    @staticmethod
    def _touch_heartbeat() -> None:
        try:
            HEARTBEAT_FILE.write_text(str(int(time.time())))
        except OSError as exc:  # pragma: no cover - filesystem edge case
            log.warning("Could not write heartbeat file: %s", exc)

    async def _get_webhook(
        self, channel: discord.TextChannel
    ) -> discord.Webhook | None:
        """Return a reusable bot-owned webhook for *channel*, creating one if needed."""
        try:
            existing = await channel.webhooks()
        except discord.Forbidden:
            log.warning(
                "Missing Manage Webhooks permission in #%s (guild=%s)",
                channel,
                getattr(channel.guild, "id", "?"),
            )
            return None
        for hook in existing:
            if hook.name == WEBHOOK_NAME and hook.user == self.user:
                return hook
        try:
            return await channel.create_webhook(name=WEBHOOK_NAME)
        except discord.Forbidden:
            log.warning("Cannot create webhook in #%s (forbidden)", channel)
            return None

    async def on_message(self, message: discord.Message) -> None:
        # Ignore our own messages and anything sent by a webhook to avoid loops.
        if message.webhook_id is not None:
            return
        if self.user is not None and message.author.id == self.user.id:
            return
        # Only operate in regular guild text channels with webhook support.
        if message.guild is None or not isinstance(
            message.channel, (discord.TextChannel, discord.Thread)
        ):
            return
        if not has_x_link(message.content or ""):
            return

        webhook_channel = message.channel
        thread = None
        if isinstance(message.channel, discord.Thread):
            thread = message.channel
            webhook_channel = message.channel.parent
            if webhook_channel is None:
                return

        webhook = await self._get_webhook(webhook_channel)
        if webhook is None:
            return

        content = _build_content(message)
        if not content:
            return

        author = message.author
        try:
            kwargs = dict(
                content=content,
                username=author.display_name,
                # Force a static PNG frame of the avatar. Discord's per-message
                # webhook avatar_url override does not render animated (a_*.gif)
                # avatars and shows blank for them, so animated avatars must be
                # requested as PNG. This is a no-op for already-static avatars.
                avatar_url=author.display_avatar.with_format("png").url,
                allowed_mentions=discord.AllowedMentions.none(),
                wait=True,
            )
            if thread is not None:
                kwargs["thread"] = thread
            await webhook.send(**kwargs)
        except discord.HTTPException as exc:
            log.warning("Failed to repost message via webhook: %s", exc)
            return

        try:
            await message.delete()
        except discord.Forbidden:
            log.warning(
                "Reposted but missing Manage Messages permission to delete original "
                "in #%s",
                message.channel,
            )
        except discord.HTTPException as exc:  # pragma: no cover - network edge
            log.warning("Failed to delete original message: %s", exc)

        log.info(
            "Rewrote x.com link(s) for %s in #%s",
            author,
            message.channel,
        )


def main() -> int:
    token = os.environ.get("TOKEN")
    if not token:
        log.error("TOKEN environment variable is not set; refusing to start.")
        return 1
    client = FixupClient()
    # discord.py reads the token directly; it is never logged.
    client.run(token, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
