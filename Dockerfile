# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.10.6 AS uv
FROM python:3.13-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY . .
RUN uv sync --frozen --no-dev --package brain-api

EXPOSE 8000
CMD ["brain-api"]
