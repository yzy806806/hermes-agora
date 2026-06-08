# === Build stage ===
FROM python:3.12-slim AS builder

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for cache
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only (no dev, no project itself)
RUN uv sync --frozen --no-dev --no-install-project

# === Production stage ===
FROM python:3.12-slim AS coordinator

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy uv for build step
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy source code
COPY coordinator/ /app/coordinator/
COPY agent_client/ /app/agent_client/
COPY __init__.py pyproject.toml plugin.yaml README.md ./

# Install project into venv (no deps, already in .venv)
RUN uv pip install -e . --no-deps

ENV PATH="/app/.venv/bin:$PATH"

# Default: start Coordinator
CMD ["agora-coordinator"]

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" || exit 1

# === Testing stage ===
FROM builder AS testing

# Copy source code
COPY coordinator/ /app/coordinator/
COPY agent_client/ /app/agent_client/
COPY __init__.py pyproject.toml plugin.yaml README.md ./
COPY tests/ /app/tests/

# Install project + dev dependencies
RUN uv sync --frozen --extra dev

ENV PATH="/app/.venv/bin:$PATH"
