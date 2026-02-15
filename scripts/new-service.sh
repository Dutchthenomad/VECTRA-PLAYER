#!/usr/bin/env bash
# Generate a new VECTRA service skeleton.
#
# Usage: ./scripts/new-service.sh <name> <layer> <upstream-port>
#
# Example:
#   ./scripts/new-service.sh feature-extractor L2 9017
#
# This creates:
#   services/<name>/
#   ├── Dockerfile
#   ├── requirements.txt
#   ├── manifest.json
#   ├── .dockerignore
#   ├── config/
#   │   └── default.yaml
#   ├── src/
#   │   ├── __init__.py
#   │   ├── main.py
#   │   ├── feed.py
#   │   └── processor.py
#   └── tests/
#       ├── __init__.py
#       ├── test_health.py
#       ├── test_envelope.py
#       └── test_processor.py

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <name> <layer> <upstream-port>"
    echo ""
    echo "  name           Service name (e.g., feature-extractor)"
    echo "  layer          Service layer: L0, L1, L2, L3, L4"
    echo "  upstream-port  Port of upstream service to consume (e.g., 9017)"
    echo ""
    echo "Layer reference:"
    echo "  L0 — Source (foundation)"
    echo "  L1 — Pipeline Core (rugs-feed, rugs-sanitizer)"
    echo "  L2 — Intelligence (feature-extractor, decision-engine)"
    echo "  L3 — Action (execution, monitoring)"
    echo "  L4 — Presentation (nexus-ui)"
    exit 1
fi

NAME="$1"
LAYER="$2"
UPSTREAM_PORT="$3"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SVC_DIR="$ROOT/services/$NAME"
REGISTRY="$ROOT/governance/projects/registry.json"

# Validate layer
if ! echo "$LAYER" | grep -qE '^L[0-4]$'; then
    echo "ERROR: Invalid layer '$LAYER'. Must be L0, L1, L2, L3, or L4."
    exit 1
fi

# Check service doesn't already exist
if [ -d "$SVC_DIR" ]; then
    echo "ERROR: Service directory already exists: $SVC_DIR"
    exit 1
fi

# Allocate next available port from PORT-ALLOCATION-SPEC ranges
# L0: 9000-9009, L1: 9010-9019, L2: 9020-9029, L3: 9030-9039, L4: 3000+
allocate_port() {
    local layer="$1"
    case "$layer" in
        L0) range_start=9000; range_end=9009 ;;
        L1) range_start=9010; range_end=9019 ;;
        L2) range_start=9020; range_end=9029 ;;
        L3) range_start=9030; range_end=9039 ;;
        L4) echo "3000"; return ;;
    esac

    # Find allocated ports from existing manifests
    for port in $(seq $range_start $range_end); do
        if ! grep -rq "\"port\": $port" "$ROOT/services/"/*/manifest.json 2>/dev/null; then
            echo "$port"
            return
        fi
    done
    echo "ERROR: No available ports in range $range_start-$range_end for layer $layer" >&2
    exit 1
}

PORT=$(allocate_port "$LAYER")
echo "Allocated port: $PORT for $NAME ($LAYER)"

# Create directory structure
mkdir -p "$SVC_DIR"/{config,src,tests}

# --- Dockerfile ---
cat > "$SVC_DIR/Dockerfile" << 'DOCKERFILE'
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/

EXPOSE ${PORT}

CMD ["python", "-m", "src.main"]
DOCKERFILE
sed -i "s/\${PORT}/$PORT/" "$SVC_DIR/Dockerfile"

# --- requirements.txt ---
cat > "$SVC_DIR/requirements.txt" << 'REQUIREMENTS'
# Service Dependencies - Pinned
fastapi==0.128.0
uvicorn==0.40.0
websockets==12.0
pyyaml==6.0.3
pydantic==2.12.5
REQUIREMENTS

# --- manifest.json ---
cat > "$SVC_DIR/manifest.json" << MANIFEST
{
  "name": "$NAME",
  "version": "1.0.0",
  "layer": "$LAYER",
  "port": $PORT,
  "upstream": "ws://localhost:$UPSTREAM_PORT/feed",
  "feeds": ["feed/data"],
  "health": "/health",
  "stats": "/stats",
  "events_consumed": [],
  "events_produced": [],
  "description": "TODO: Add service description"
}
MANIFEST

# --- .dockerignore ---
cat > "$SVC_DIR/.dockerignore" << 'DOCKERIGNORE'
__pycache__/
*.pyc
.pytest_cache/
tests/
.venv/
*.egg-info/
.git/
.ruff_cache/
DOCKERIGNORE

# --- config/default.yaml ---
cat > "$SVC_DIR/config/default.yaml" << YAML
service:
  name: $NAME
  port: $PORT
  log_level: INFO

upstream:
  url: ws://localhost:$UPSTREAM_PORT/feed
  reconnect_delay: 2.0
  max_reconnect_delay: 30.0
YAML

# --- src/__init__.py ---
touch "$SVC_DIR/src/__init__.py"

# --- src/main.py ---
cat > "$SVC_DIR/src/main.py" << 'MAIN'
"""Service entry point with FastAPI app."""

import asyncio
import logging
import os
import time

import uvicorn
from fastapi import FastAPI

from .feed import FeedManager
from .processor import Processor

logger = logging.getLogger(__name__)

app = FastAPI(title=os.getenv("SERVICE_NAME", "service"))

start_time = time.time()
processor = Processor()
feed_manager = FeedManager(processor=processor)
_background_tasks: set[asyncio.Task] = set()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "uptime": time.time() - start_time,
    }


@app.get("/stats")
async def stats():
    return processor.get_stats()


@app.on_event("startup")
async def startup():
    task = asyncio.create_task(feed_manager.connect())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@app.on_event("shutdown")
async def shutdown():
    await feed_manager.disconnect()


if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
MAIN

# --- src/feed.py ---
cat > "$SVC_DIR/src/feed.py" << 'FEED'
"""WebSocket upstream consumer and downstream publisher."""

import asyncio
import json
import logging
import os

import websockets

logger = logging.getLogger(__name__)


class FeedManager:
    """Connects to upstream WebSocket and forwards processed events."""

    def __init__(self, processor):
        self.processor = processor
        self.upstream_url = os.getenv("UPSTREAM_URL", "ws://localhost:9000/feed")
        self._ws = None
        self._running = False

    async def connect(self):
        self._running = True
        while self._running:
            try:
                async with websockets.connect(self.upstream_url) as ws:
                    self._ws = ws
                    logger.info("Connected to upstream: %s", self.upstream_url)
                    async for message in ws:
                        data = json.loads(message)
                        await self.processor.process(data)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Upstream connection closed, reconnecting...")
            except Exception:
                logger.exception("Upstream connection error")
            if self._running:
                await asyncio.sleep(2.0)

    async def disconnect(self):
        self._running = False
        if self._ws:
            await self._ws.close()
FEED

# --- src/processor.py ---
cat > "$SVC_DIR/src/processor.py" << 'PROCESSOR'
"""Business logic processor — implement your service logic here."""

import logging

logger = logging.getLogger(__name__)


class Processor:
    """Process incoming events from the upstream feed."""

    def __init__(self):
        self._events_processed = 0

    async def process(self, event: dict) -> None:
        """Process a single event from the upstream feed.

        Override this method with your service's business logic.
        """
        self._events_processed += 1

    def get_stats(self) -> dict:
        return {
            "events_processed": self._events_processed,
        }
PROCESSOR

# --- tests/__init__.py ---
touch "$SVC_DIR/tests/__init__.py"

# --- tests/test_health.py ---
cat > "$SVC_DIR/tests/test_health.py" << 'TEST_HEALTH'
"""Health endpoint contract test."""

from unittest.mock import patch

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("src.main.feed_manager"):
        from src.main import app
        return TestClient(app)


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client):
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "uptime" in data
    assert data["status"] == "healthy"
    assert isinstance(data["uptime"], (int, float))
TEST_HEALTH

# --- tests/test_envelope.py ---
cat > "$SVC_DIR/tests/test_envelope.py" << 'TEST_ENVELOPE'
"""Envelope format compliance test."""

import json


def test_envelope_has_required_fields():
    """Standard envelope must have event_type, timestamp, service, data."""
    envelope = {
        "event_type": "test.event",
        "timestamp": "2026-01-01T00:00:00Z",
        "service": "test-service",
        "channel": "feed/data",
        "data": {"key": "value"},
    }
    required = ["event_type", "timestamp", "service", "data"]
    for field in required:
        assert field in envelope, f"Missing required field: {field}"


def test_envelope_serializable():
    """Envelope must be JSON-serializable."""
    envelope = {
        "event_type": "test.event",
        "timestamp": "2026-01-01T00:00:00Z",
        "service": "test-service",
        "channel": "feed/data",
        "data": {"key": "value"},
    }
    serialized = json.dumps(envelope)
    deserialized = json.loads(serialized)
    assert deserialized == envelope
TEST_ENVELOPE

# --- tests/test_processor.py ---
cat > "$SVC_DIR/tests/test_processor.py" << 'TEST_PROCESSOR'
"""Business logic tests — add your service-specific tests here."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor import Processor


@pytest.fixture
def processor():
    return Processor()


@pytest.mark.asyncio
async def test_processor_processes_event(processor):
    await processor.process({"event_type": "test", "data": {}})
    stats = processor.get_stats()
    assert stats["events_processed"] == 1


@pytest.mark.asyncio
async def test_processor_counts_events(processor):
    for _ in range(5):
        await processor.process({"event_type": "test", "data": {}})
    assert processor.get_stats()["events_processed"] == 5
TEST_PROCESSOR

echo ""
echo "Service '$NAME' created at: $SVC_DIR"
echo "  Layer: $LAYER"
echo "  Port: $PORT"
echo "  Upstream: ws://localhost:$UPSTREAM_PORT/feed"
echo ""
echo "Next steps:"
echo "  1. Edit src/processor.py with your business logic"
echo "  2. Update manifest.json events_consumed/events_produced"
echo "  3. Run tests: pytest services/$NAME/tests/ -v"
echo "  4. Build Docker: docker build -t vectra/$NAME services/$NAME/"
