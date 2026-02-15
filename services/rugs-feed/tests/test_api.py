"""Tests for FastAPI application."""

import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, "services/rugs-feed")

from src.api import create_app


class TestAPI:
    """Test API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            app = create_app(db_path=f.name, auto_connect=False)
            yield TestClient(app)

    def test_health_endpoint(self, client):
        """Health endpoint should return service info."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rugs-feed"

    def test_games_endpoint(self, client):
        """Games endpoint should return empty list initially."""
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert isinstance(data["games"], list)

    def test_seeds_endpoint(self, client):
        """Seeds endpoint should return empty list initially."""
        response = client.get("/api/seeds")
        assert response.status_code == 200
        data = response.json()
        assert "seeds" in data
        assert isinstance(data["seeds"], list)

    def test_export_endpoint(self, client):
        """Export endpoint should return PRNG attack format."""
        response = client.get("/api/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"
