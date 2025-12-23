"""
Tests for vector_indexer chunker.py

Tests cover:
- JSON serialization with non-serializable types (Decimals, datetimes, etc.)
- Chunk ID uniqueness
- Event chunking for different doc types
"""

from datetime import datetime
from decimal import Decimal

import pytest

from services.vector_indexer.chunker import _format_raw_json, chunk_event


class TestFormatRawJson:
    """Tests for _format_raw_json helper function"""

    def test_format_dict_with_decimals(self):
        """Test formatting dict with Decimal values"""
        event = {
            "raw_json": {
                "price": Decimal("1.23"),
                "quantity": Decimal("100.00"),
            }
        }
        result = _format_raw_json(event)
        assert "1.23" in result
        assert "100.00" in result
        assert isinstance(result, str)

    def test_format_dict_with_datetime(self):
        """Test formatting dict with datetime values"""
        dt = datetime(2025, 12, 22, 18, 0, 0)
        event = {"raw_json": {"timestamp": dt, "event": "test"}}
        result = _format_raw_json(event)
        assert "2025-12-22" in result
        assert "18:00:00" in result
        assert isinstance(result, str)

    def test_format_dict_with_mixed_types(self):
        """Test formatting dict with mixed non-serializable types"""
        dt = datetime(2025, 12, 22, 18, 0, 0)
        event = {
            "raw_json": {
                "price": Decimal("1.23"),
                "timestamp": dt,
                "name": "test",
                "count": 42,
            }
        }
        result = _format_raw_json(event)
        assert "1.23" in result
        assert "2025-12-22" in result
        assert "test" in result
        assert "42" in result

    def test_format_string_raw_json(self):
        """Test formatting when raw_json is already a string"""
        event = {"raw_json": '{"test": "value"}'}
        result = _format_raw_json(event)
        assert result == '{"test": "value"}'

    def test_format_missing_raw_json(self):
        """Test formatting when raw_json is missing"""
        event = {}
        result = _format_raw_json(event)
        assert result == "{}"

    def test_format_none_raw_json(self):
        """Test formatting when raw_json is None"""
        event = {"raw_json": None}
        result = _format_raw_json(event)
        assert result == "None"


class TestChunkEvent:
    """Tests for chunk_event function"""

    def test_chunk_id_uniqueness(self):
        """Test chunk IDs are unique with timestamp"""
        event1 = {
            "session_id": "session-1",
            "seq": 0,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "ws_event",
            "raw_json": {},
        }
        event2 = {
            "session_id": "session-1",
            "seq": 0,
            "ts": "2025-12-22T18:00:01",
            "doc_type": "ws_event",
            "raw_json": {},
        }
        chunk1 = chunk_event(event1)
        chunk2 = chunk_event(event2)

        # Same session_id and seq, but different timestamp
        assert chunk1["id"] != chunk2["id"]
        assert "2025-12-22T18:00:00" in chunk1["id"]
        assert "2025-12-22T18:00:01" in chunk2["id"]

    def test_chunk_id_includes_all_fields(self):
        """Test chunk ID includes session_id, seq, and timestamp"""
        event = {
            "session_id": "test-session",
            "seq": 42,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "ws_event",
            "raw_json": {},
        }
        chunk = chunk_event(event)

        assert "test-session" in chunk["id"]
        assert "42" in chunk["id"]
        assert "2025-12-22T18:00:00" in chunk["id"]

    def test_chunk_ws_event_with_decimals(self):
        """Test chunking WebSocket event with Decimal values"""
        event = {
            "session_id": "session-1",
            "seq": 1,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "ws_event",
            "direction": "received",
            "game_id": "game-123",
            "raw_json": {
                "price": Decimal("1.5"),
                "quantity": Decimal("100"),
            },
        }
        chunk = chunk_event(event)

        assert chunk["id"]
        assert "WebSocket Event" in chunk["text"]
        assert "1.5" in chunk["text"]
        assert "100" in chunk["text"]
        assert chunk["metadata"]["doc_type"] == "ws_event"

    def test_chunk_game_tick_with_datetime(self):
        """Test chunking game tick with datetime"""
        dt = datetime(2025, 12, 22, 18, 0, 0)
        event = {
            "session_id": "session-1",
            "seq": 2,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "game_tick",
            "game_id": "game-123",
            "raw_json": {
                "timestamp": dt,
                "tick": 5,
            },
        }
        chunk = chunk_event(event)

        assert "Game Tick" in chunk["text"]
        assert "2025-12-22" in chunk["text"]
        assert chunk["metadata"]["doc_type"] == "game_tick"

    def test_chunk_player_action(self):
        """Test chunking player action"""
        event = {
            "session_id": "session-1",
            "seq": 3,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "player_action",
            "game_id": "game-123",
            "player_id": "player-1",
            "raw_json": {"action": "buy", "amount": Decimal("10")},
        }
        chunk = chunk_event(event)

        assert "Player Action" in chunk["text"]
        assert "player-1" in chunk["text"]
        assert chunk["metadata"]["doc_type"] == "player_action"

    def test_chunk_server_state(self):
        """Test chunking server state"""
        event = {
            "session_id": "session-1",
            "seq": 4,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "server_state",
            "game_id": "game-123",
            "raw_json": {"state": "active"},
        }
        chunk = chunk_event(event)

        assert "Server State Update" in chunk["text"]
        assert chunk["metadata"]["doc_type"] == "server_state"

    def test_chunk_system_event(self):
        """Test chunking system event"""
        event = {
            "session_id": "session-1",
            "seq": 5,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "system_event",
            "source": "websocket",
            "raw_json": {"event": "connected"},
        }
        chunk = chunk_event(event)

        assert "System Event" in chunk["text"]
        assert chunk["metadata"]["doc_type"] == "system_event"

    def test_chunk_generic_unknown_type(self):
        """Test chunking unknown doc type"""
        event = {
            "session_id": "session-1",
            "seq": 6,
            "ts": "2025-12-22T18:00:00",
            "doc_type": "unknown_type",
            "raw_json": {"data": "test"},
        }
        chunk = chunk_event(event)

        assert "Event" in chunk["text"]
        assert "unknown_type" in chunk["text"]
        assert chunk["metadata"]["doc_type"] == "unknown_type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
