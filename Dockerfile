# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev


FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd -r weatherflow && useradd -r -g weatherflow weatherflow

WORKDIR /app/weatherflow-collector

COPY --from=builder /app/.venv /app/.venv

COPY src/ ./src/

RUN mkdir -p logs api_data_saver export cache && \
    chown -R weatherflow:weatherflow /app/weatherflow-collector /app/.venv

USER weatherflow

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

EXPOSE 6789 50222/udp

CMD ["python3", "src/weatherflow-collector.py"]
