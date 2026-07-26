FROM node:22-alpine AS web
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN mkdir -p /build/app/static && npm run build

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

RUN uv venv /app/.venv \
 && uv pip install --python /app/.venv/bin/python \
      "fastapi>=0.115.0" \
      "uvicorn[standard]>=0.32.0" \
      "pydantic-settings>=2.6.0" \
      "httpx>=0.27.0" \
      "sqlmodel>=0.0.22" \
      "segno>=1.6.0" \
      "taskiq>=0.11.0"

COPY app ./app
COPY --from=web /build/app/static/web ./app/static/web
COPY app/static/logo.png ./app/static/logo.png
COPY app/static/embed.js ./app/static/embed.js

RUN mkdir -p /app/data

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
