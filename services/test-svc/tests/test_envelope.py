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
