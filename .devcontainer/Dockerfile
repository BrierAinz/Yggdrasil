FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y \
        git \
        pre-commit \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python tools
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    httpx \
    ruff \
    pre-commit
