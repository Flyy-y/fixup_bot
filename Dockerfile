# syntax=docker/dockerfile:1

# ---- Builder: install dependencies into an isolated prefix ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---- Runtime: minimal image, non-root, no build tooling ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEARTBEAT_FILE=/tmp/fixupx_healthy

# Copy installed dependencies from the builder stage.
COPY --from=builder /install /usr/local

# Create an unprivileged user to run the bot.
RUN useradd --create-home --uid 10001 botuser

WORKDIR /app
COPY --chown=botuser:botuser src/ ./src/
COPY --chown=botuser:botuser healthcheck.py ./

USER botuser

# Token is injected at runtime via the TOKEN env var; never baked into the image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

ENTRYPOINT ["python", "-m", "src.bot"]
