# =====================================
# STAGE 1: BUILDER
# =====================================
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps (build only)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies globally (NO .venv)
RUN uv sync --frozen --no-install-project --system

# =====================================
# STAGE 2: RUNTIME
# =====================================
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Copy app code
COPY src ./src
COPY configs ./configs

ENV PYTHONPATH=/app/src

# Reduce Python overhead
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Start API
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"] 


#================================================================================
#docker build -f docker/model.Dockerfile -t epp-sla-hourly-anomaly-model .
#docker build -f docker/dashboard.Dockerfile -t epp-sla-hourly-anomaly-ui .
#=====================================================================================