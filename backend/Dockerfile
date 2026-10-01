# Build context is backend/ only — changes in bot/ or frontend/ never invalidate this image.
# Targets: `api` (FastAPI) and `worker` (Taskiq). Both share the dependency layers below, so a code change
# rebuilds only the final COPY layer. The worker will add Chromium for PDFs (ADR 0005) in its own stage.

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/uv
WORKDIR /app

# 1) dependencies only — cached until pyproject.toml / uv.lock change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# 2) application code
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN useradd --create-home --uid 10001 app
USER app

FROM base AS api
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]
# --proxy-headers trusts X-Forwarded-For only from FORWARDED_ALLOW_IPS (env) — set it to the Caddy address
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

FROM base AS worker
CMD ["taskiq", "worker", "app.worker:broker"]
