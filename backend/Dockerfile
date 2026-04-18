# syntax=docker/dockerfile:1.7

# ---------- base ----------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

# ---------- dev ----------
FROM base AS dev
RUN pip install -e ".[dev]"
COPY . .
EXPOSE 8000
CMD ["uvicorn", "meoxa_secretary.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- prod ----------
FROM base AS prod
COPY . .
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "meoxa_secretary.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
