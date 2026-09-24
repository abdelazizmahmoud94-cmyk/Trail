FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt \
    && pip install --no-cache-dir --user scikit-learn

FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="ARHPP" \
      org.opencontainers.image.version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/* \
    && groupadd -r arhpp && useradd -r -g arhpp arhpp

WORKDIR /app

COPY --from=builder /root/.local /home/arhpp/.local
ENV PATH=/home/arhpp/.local/bin:$PATH

COPY --chown=arhpp:arhpp . /app

RUN mkdir -p /app/excel_input /app/arhpp/ml/models && \
    chown -R arhpp:arhpp /app

USER arhpp

EXPOSE 8000 14200

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "api.server"]
