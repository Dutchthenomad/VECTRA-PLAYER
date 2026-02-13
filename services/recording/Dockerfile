FROM python:3.12-slim

LABEL maintainer="VECTRA Team"
LABEL description="Recording Service - Captures game data via gameHistory extraction"
LABEL version="1.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Copy Foundation package from parent project
# This is mounted as a volume in docker-compose for development
# In production, copy the foundation package
COPY --from=foundation /app/src/foundation ./foundation/ 2>/dev/null || true

# Create data directory
RUN mkdir -p /data/raw_captures

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=9010
ENV HOST=0.0.0.0
ENV FOUNDATION_WS_URL=ws://host.docker.internal:9000/feed
ENV STORAGE_PATH=/data/raw_captures
ENV AUTO_START_RECORDING=true

# Expose API port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run service
CMD ["python", "-m", "src.main"]
