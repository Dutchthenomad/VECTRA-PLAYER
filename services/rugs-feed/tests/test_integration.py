"""Integration tests for Rugs Feed Service."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "services/rugs-feed")

from fastapi.testclient import TestClient
from src.api import create_app
from src.client import CapturedEvent, ConnectionState, RugsFeedClient
from src.storage import EventStorage


class TestIntegration:
    """Test full service integration."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_event_flow(self, temp_db):
        """Test event capture through storage to API."""
        # Setup storage
        storage = EventStorage(temp_db)
        await storage.initialize()

        # Simulate captured event
        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-integration",
                "price": 3.5,
                "tickCount": 200,
                "rugged": True,
                "provablyFair": {
                    "serverSeed": "integration-test-seed-12345",
                    "serverSeedHash": "hash-abc123",
                },
            },
            game_id="20260204-integration",
        )

        # Store event
        await storage.store_event(event)

        # Verify via API
        app = create_app(db_path=temp_db, auto_connect=False)
        with TestClient(app) as client:
            # Check games endpoint
            response = client.get("/api/games")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["games"][0]["game_id"] == "20260204-integration"

            # Check seeds endpoint
            response = client.get("/api/seeds")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["seeds"][0]["server_seed"] == "integration-test-seed-12345"

            # Check export endpoint
            response = client.get("/api/export")
            assert response.status_code == 200
            assert "integration-test-seed" in response.text

        await storage.close()

    def test_client_initialization(self):
        """Test client can be initialized without connection."""
        client = RugsFeedClient()
        assert client.state == ConnectionState.DISCONNECTED
        assert "backend.rugs.fun" in client.url
        assert not client.is_connected


class TestHealthEndpoint:
    """Test health endpoint integration."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_health_returns_stats(self, temp_db):
        """Health endpoint should return service statistics."""
        app = create_app(db_path=temp_db, auto_connect=False)
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "uptime_seconds" in data
            assert "stats" in data
