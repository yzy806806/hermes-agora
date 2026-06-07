FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for cache
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev (pytest etc.)
RUN uv sync --frozen --all-extras --no-install-project

# Copy source code
COPY . .

# Install project (without re-resolving)
RUN uv pip install -e . --no-deps

# Default: run tests
CMD [".venv/bin/pytest", "-x", "-q", "--tb=short"]
