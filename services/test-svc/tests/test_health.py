"""Health endpoint contract test."""

from unittest.mock import patch

import pytest
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
