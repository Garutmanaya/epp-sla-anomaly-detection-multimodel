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
RUN uv pip install --system --no-cache -r pyproject.toml

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
# Migrate to S3
COPY models  ./models
# Need pyproject.toml to identify the root
COPY pyproject.toml uv.lock ./

ENV PYTHONPATH=/app/src

# Reduce Python overhead
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Start API
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"] 


#================================================================================
#docker build -f docker/app.Dockerfile -t epp-sla-anomaly-detection-multimodel .
# run 
#docker run -it  -p 8000:8000 epp-sla-anomaly-detection-multimodel:latest
#=====================================================================================
