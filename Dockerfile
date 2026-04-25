# syntax=docker/dockerfile:1.7

# ─── Builder stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt \
 && pip install gunicorn==23.0.0


# ─── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=morph.settings \
    PORT=8000 \
    GUNICORN_WORKERS=4 \
    GUNICORN_TIMEOUT=60

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 \
      curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system morpheus \
 && useradd --system --gid morpheus --home-dir /app --no-create-home morpheus

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=morpheus:morpheus . /app

# Ensure the entrypoint is executable inside the image even if the host bit was lost.
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Bake collected static into the image so admin + dashboard CSS/JS exist
# even when the staticfiles volume is empty/unwritable. SECRET_KEY/DB are
# not needed for collectstatic; pass placeholders to satisfy settings.py.
RUN SECRET_KEY=build-only \
    ALLOWED_HOSTS=localhost \
    CORS_ALLOWED_ORIGINS=http://localhost \
    DATABASE_URL=sqlite:///:memory: \
    DEBUG=False \
    python manage.py collectstatic --noinput

USER morpheus
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/healthz || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["web"]
