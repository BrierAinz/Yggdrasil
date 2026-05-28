# Horror GameMaster — Dockerfile
# Multi-stage build for minimal image

FROM python:3.14-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .
COPY data/ data/
COPY deploy/Modelfile.template deploy/

# Install Python deps
RUN pip install --no-cache-dir \
    pydantic>=2.0 \
    numpy>=1.24 \
    rich>=13.0 \
    fastapi>=0.100 \
    uvicorn>=0.23 \
    requests>=2.31 \
    openai>=1.0

# Copy source
COPY src/ src/

# Expose web UI port
EXPOSE 8080

# Default: run web UI
CMD ["python", "-m", "src.web_ui", "--host", "0.0.0.0", "--port", "8080"]
