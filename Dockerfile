FROM python:3.14-slim

LABEL maintainer="BrierStudios"
LABEL description="Lilith Agent — Dark Goddess of Yggdrasil Digital"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY lilith_agent.py .
COPY LILITH_README.md LILITH_ROADMAP.md LILITH_TOOLS.md ./

# Create config directories
RUN mkdir -p /app/.lilith/skills /app/.lilith/plugins /app/.lilith/context /app/.lilith/undo /app/.lilith/audio

# Default entrypoint
ENTRYPOINT ["python3", "lilith_agent.py"]
CMD ["--provider", "deepseek"]
