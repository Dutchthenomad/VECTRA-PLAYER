"""
Tests for Recording Service API endpoints.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Mock the subscriber for API tests
class MockStats:
    """Mock recording stats."""

    is_recording = True
    session_games = 5
    today_games = 10
    total_games = 100
    deduped_count = 50
    last_rug_multiplier = 1.5
    last_rug_time = datetime(2026, 1, 19, 12, 0, 0)
    session_start = datetime(2026, 1, 19, 10, 0, 0)


class MockStorage:
    """Mock storage."""

    def get_storage_stats(self):
        return {
            "storage_path": "/data/games",
            "total_size_bytes": 1024 * 1024,
            "total_size_mb": 1.0,
            "file_count": 5,
            "buffer_size": 0,
            "parquet_available": True,
        }


class MockSubscriber:
    """Mock subscriber for API testing."""

    def __init__(self):
        self._connected = True
        self._stats = MockStats()
        self._storage = MockStorage()
        self._recording = True

    @property
    def stats(self):
        return self._stats

    @property
    def is_recording(self):
        return self._recording

    def start_recording(self):
        if self._recording:
            return False
        self._recording = True
        self._stats.is_recording = True
        return True

    def stop_recording(self):
        if not self._recording:
            return False
        self._recording = False
        self._stats.is_recording = False
        return True

    def get_recent_games(self, limit=10):
        return [
            {
                "gameId": f"game-{i}",
                "tickCount": 100 + i * 10,
                "price": 1.0 + i * 0.1,
                "_captured_at": "2026-01-19T12:00:00",
            }
            for i in range(min(limit, 5))
        ]


# Import API module
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.api import create_app


@pytest.fixture
def client():
    """Create test client with mock subscriber."""
    with tempfile.TemporaryDirectory() as tmpdir:
        subscriber = MockSubscriber()
        app = create_app(
            subscriber=subscriber,
            config_path=Path(tmpdir),
            start_time=datetime(2026, 1, 19, 10, 0, 0),
        )
        yield TestClient(app), subscriber


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200."""
        test_client, _ = client
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """Health response should have required fields."""
        test_client, _ = client
        response = test_client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "recording-service"
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data
        assert "foundation_connected" in data


class TestRecordingStatusEndpoint:
    """Tests for /recording/status endpoint."""

    def test_status_returns_200(self, client):
        """Status endpoint should return 200."""
        test_client, _ = client
        response = test_client.get("/recording/status")
        assert response.status_code == 200

    def test_status_response_structure(self, client):
        """Status response should have required fields."""
        test_client, _ = client
        response = test_client.get("/recording/status")
        data = response.json()

        assert "enabled" in data
        assert "games_captured" in data
        assert "session_start" in data


class TestRecordingToggleEndpoints:
    """Tests for /recording/start and /recording/stop endpoints."""

    def test_stop_when_recording(self, client):
        """Stop should succeed when recording is active."""
        test_client, subscriber = client
        subscriber._recording = True
        subscriber._stats.is_recording = True

        response = test_client.post("/recording/stop")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is False

    def test_stop_when_already_stopped(self, client):
        """Stop should fail when already stopped."""
        test_client, subscriber = client
        subscriber._recording = False
        subscriber._stats.is_recording = False

        response = test_client.post("/recording/stop")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False

    def test_start_when_stopped(self, client):
        """Start should succeed when recording is stopped."""
        test_client, subscriber = client
        subscriber._recording = False
        subscriber._stats.is_recording = False

        response = test_client.post("/recording/start")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is True

    def test_start_when_already_recording(self, client):
        """Start should fail when already recording."""
        test_client, subscriber = client
        subscriber._recording = True
        subscriber._stats.is_recording = True

        response = test_client.post("/recording/start")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False


class TestStatsEndpoint:
    """Tests for /recording/stats endpoint."""

    def test_stats_returns_200(self, client):
        """Stats endpoint should return 200."""
        test_client, _ = client
        response = test_client.get("/recording/stats")
        assert response.status_code == 200

    def test_stats_response_structure(self, client):
        """Stats response should have required fields."""
        test_client, _ = client
        response = test_client.get("/recording/stats")
        data = response.json()

        assert "session" in data
        assert "today" in data
        assert "total" in data
        assert "deduped" in data
        assert "storage" in data


class TestRecentGamesEndpoint:
    """Tests for /recording/recent endpoint."""

    def test_recent_returns_200(self, client):
        """Recent endpoint should return 200."""
        test_client, _ = client
        response = test_client.get("/recording/recent")
        assert response.status_code == 200

    def test_recent_respects_limit(self, client):
        """Recent endpoint should respect limit parameter."""
        test_client, _ = client
        response = test_client.get("/recording/recent?limit=3")
        data = response.json()

        assert len(data) <= 3

    def test_recent_rejects_excessive_limit(self, client):
        """Recent endpoint should reject limit > 100."""
        test_client, _ = client
        response = test_client.get("/recording/recent?limit=200")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
