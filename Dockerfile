# Optional stdio container; no remote transport or listener is configured.
FROM python:3.12-slim-bookworm
WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.25
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER 10001:10001
ENTRYPOINT ["formtrace-mcp"]
