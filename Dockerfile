# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.10.6 AS uv
FROM python:3.13-slim AS api

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

FROM node:22-slim AS web-build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
RUN npm run build:app --workspace @brain/web

FROM node:22-slim AS web
ENV NODE_ENV=production
WORKDIR /app
COPY --from=web-build /app/apps/web/.next/standalone ./
COPY --from=web-build /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=web-build /app/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
