#!/usr/bin/env python3
"""LOCAL-ONLY live smoke test.

Connects to Discord with the real ``TOKEN`` from the environment (or a local
``.env``), posts a message containing an ``x.com`` link into a test channel,
waits for the bot to delete + repost it as ``fixupx.com`` via webhook, asserts
the transformation happened, then cleans up the reposted message.

This is NEVER run in CI (CI has no token). Run it locally:

    export TOKEN=...                 # or rely on .env
    export SMOKE_CHANNEL_ID=123...   # a text channel the bot can manage
    python tests/smoke_test.py

It requires the bot process to be running and connected to the same channel.
"""

import asyncio
import os
import sys
from pathlib import Path

import discord

from src.url_transform import transform_text

TEST_LINK = "https://x.com/jack/status/20"
EXPECTED = transform_text(TEST_LINK)  # https://fixupx.com/jack/status/20


def _load_dotenv() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


async def run() -> int:
    _load_dotenv()
    token = os.environ.get("TOKEN")
    channel_id = os.environ.get("SMOKE_CHANNEL_ID")
    if not token or not channel_id:
        print("TOKEN and SMOKE_CHANNEL_ID must be set for the smoke test.")
        return 2

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    result = {"ok": False}

    @client.event
    async def on_ready() -> None:
        try:
            channel = await client.fetch_channel(int(channel_id))
            sent = await channel.send(f"smoke test {TEST_LINK}")
            print(f"Posted test message id={sent.id}; waiting for bot to fix it...")

            await asyncio.sleep(8)

            found = None
            async for msg in channel.history(limit=25):
                if EXPECTED in (msg.content or ""):
                    found = msg
                    break

            if found is None:
                print("FAIL: no message with fixupx.com found.")
            else:
                print(f"PASS: found reposted message with {EXPECTED!r}")
                result["ok"] = True
                await found.delete()
                print("Cleaned up reposted message.")
        finally:
            await client.close()

    await client.start(token)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
