FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 atalaya \
    && useradd  --system --uid 1001 --gid atalaya --home /app --shell /usr/sbin/nologin atalaya \
    && mkdir -p /var/atalaya/evidence /var/atalaya/reports /var/atalaya/logs \
    && chown -R atalaya:atalaya /app /var/atalaya

COPY --chown=atalaya:atalaya requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=atalaya:atalaya . .

USER atalaya

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips=*"]
