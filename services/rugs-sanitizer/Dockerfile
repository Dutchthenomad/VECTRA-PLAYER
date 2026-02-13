# Rugs Sanitizer Service Dockerfile
# Sanitized, typed, categorized WebSocket feed for rugs.fun

FROM python:3.12-slim

LABEL maintainer="VECTRA Team"
LABEL description="WebSocket feed sanitization service for rugs.fun events"
LABEL version="1.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=9017

# Expose API port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the service
CMD ["python", "-m", "src.main"]
