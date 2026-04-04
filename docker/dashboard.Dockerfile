# =====================================
# STAGE 1: BUILDER
# =====================================
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --system

# =====================================
# STAGE 2: RUNTIME
# =====================================
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY src ./src
COPY dashboard ./dashboard
COPY configs ./configs

ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]


#================================================================================
#docker build -f docker/model.Dockerfile -t epp-sla-hourly-anomaly-model .
#docker build -f docker/dashboard.Dockerfile -t epp-sla-hourly-anomaly-ui .
#=====================================================================================