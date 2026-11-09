# Multi-stage build using Astral uv for ultra-fast dependency management
FROM ghcr.io/astral-sh/uv:0.5.26-python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and install project
COPY src/ ./src/
COPY README.md ./
RUN uv sync --frozen --no-dev

# Final runtime image
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Create unprivileged application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy virtual environment and project from builder
COPY --from=builder --chown=appuser:appuser /app /app

# Create directory for local data persistence
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV NUTRITION_DATA_PATH=/app/data/nutrition_logs.json

USER appuser

EXPOSE 8000

ENTRYPOINT ["fitness-mcp-server"]
CMD ["--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
