# syntax=docker/dockerfile:1

# --- Builder: resolve and install dependencies with uv ----------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer only rebuilds when the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then the project itself, non-editable, so the venv is self-contained.
COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# --- Runtime: slim image, venv only, unprivileged user ------------------------
FROM python:3.13-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="sushiro-mcp" \
    org.opencontainers.image.description="Unofficial MCP server exposing the Sushiro Hong Kong SushiPass queue API as tools (educational/research; not affiliated with or endorsed by Sushiro)" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.authors="Jaguar-Kwok"

RUN groupadd --system app && useradd --system --gid app --create-home app

RUN mkdir -p /app && chown app:app /app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('MCP_PORT', '8000')}/health\", timeout=4)"]

CMD ["sushiro-mcp"]
