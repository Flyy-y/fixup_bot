# fixupx-bot

A small, containerized Discord bot that fixes broken Twitter/X embeds. When a
message contains an `x.com` link, the bot deletes the original message and
reposts an identical copy with the host rewritten to `fixupx.com`, so Discord
renders a working embed. The repost is sent through a channel **webhook**
impersonating the original author (same username and avatar) to preserve the
look and feel of the conversation.

> `https://x.com/jack/status/20` → `https://fixupx.com/jack/status/20`

## How it works

- Detects `http(s)://x.com/...` and `http(s)://www.x.com/...` links (host match
  is case-insensitive). Only the **host** is rewritten; scheme, `www.` prefix,
  port, path, query string and fragment are preserved.
- Handles multiple links in a single message.
- Rewrites only genuine `x.com` hosts. Look-alikes such as `xx.com`,
  `max.com`, `x.com.evil.com`, `fixupx.com` and `x.com` appearing inside a path
  are left untouched.
- If at least one link is rewritten, the original is deleted and the fixed
  version is reposted via webhook. Attachments are handled best-effort by
  re-injecting their URLs into the reposted content.
- Ignores its own messages and any message sent by a webhook, preventing loops.
- Does nothing when no `x.com` link is present.
- Never logs the token.

## Configuration

| Variable            | Required | Default              | Description                                              |
| ------------------- | -------- | -------------------- | -------------------------------------------------------- |
| `TOKEN`             | yes      | —                    | Discord bot token. Read at runtime; never baked in.      |
| `LOG_LEVEL`         | no       | `INFO`               | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).     |
| `HEARTBEAT_FILE`    | no       | `/tmp/fixupx_healthy`| Path of the healthcheck heartbeat file.                  |
| `HEARTBEAT_MAX_AGE` | no       | `90`                 | Max heartbeat age (seconds) before the container is unhealthy. |
| `SMOKE_CHANNEL_ID`  | no       | —                    | Channel ID used only by the local live smoke test.       |

### Required Discord setup

- Enable the **Message Content Intent** in the Developer Portal.
- Grant the bot **Manage Messages**, **Manage Webhooks** and **Send Messages**
  on the target server.

## Run with Docker

The published multi-arch image (`linux/amd64`, `linux/arm64`) lives on GHCR:

```
ghcr.io/flyy-y/fixup_bot:latest
```

```bash
docker run -d --name fixupx-bot \
  --restart unless-stopped \
  -e TOKEN="your-discord-bot-token" \
  ghcr.io/flyy-y/fixup_bot:latest
```

Or with an env file (recommended — keeps the token out of your shell history):

```bash
docker run -d --name fixupx-bot --restart unless-stopped \
  --env-file .env \
  ghcr.io/flyy-y/fixup_bot:latest
```

## Local development

```bash
# 1. Provide your token (this file is git-ignored)
cp .env.example .env
# edit .env and set TOKEN=...

# 2. Run unit tests
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=src.url_transform --cov-report=term-missing

# 3. Run the bot locally via docker compose (reads .env)
docker compose up --build
```

### Live smoke test (local only)

The smoke test posts a real `x.com` link into a test channel, waits for the bot
to fix it, asserts the rewrite happened, then cleans up. It needs a real token
and is **never** run in CI.

```bash
# Bot must be running and present in the channel
export SMOKE_CHANNEL_ID=123456789012345678   # or set it in .env
python tests/smoke_test.py
```

## Security

- `.env` and the token are git-ignored and never committed or built into the
  image. The image runs as a non-root user with a healthcheck.
- CI enforces: **gitleaks** (secret detection over full history), **pip-audit**
  (dependency CVEs), **Semgrep** (SAST), **hadolint** (Dockerfile lint) and
  **Trivy** (filesystem + built image, failing on critical vulnerabilities).

## CI/CD

GitHub Actions runs on every push and pull request:

1. **Lint & unit tests** — `ruff` + `pytest` with a 100% coverage gate on the
   URL transformation logic.
2. **Security scans** — gitleaks, pip-audit, Semgrep, hadolint, Trivy (fs).
3. **Build & publish** — multi-arch (`amd64` + `arm64`) image built with
   `docker buildx` + QEMU, tagged via `docker/metadata-action`, pushed to GHCR,
   then scanned with Trivy (fails on critical vulnerabilities). Images are
   published only on branch/tag pushes, not on pull requests.

## License

MIT
