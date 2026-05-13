FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ../requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

COPY --chown=appuser:appuser ../app ./app
COPY --chown=appuser:appuser ../dashboard ./dashboard
COPY --chown=appuser:appuser ../sample_data ./sample_data

RUN mkdir -p /app/data && chown appuser:appuser /app/data

EXPOSE 8000 8501

COPY --chown=appuser:appuser ../docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
