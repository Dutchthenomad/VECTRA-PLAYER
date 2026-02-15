"""Tests for EventStorage."""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, "services/rugs-feed")

from src.client import CapturedEvent
from src.storage import EventStorage


class TestEventStorage:
    """Test EventStorage SQLite layer."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, temp_db):
        """Storage should create tables on init."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        # Should have games and events tables
        games = await storage.get_recent_games(limit=10)
        assert games == []

    @pytest.mark.asyncio
    async def test_store_game_state_event(self, temp_db):
        """Should store gameStateUpdate events."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-test123",
                "price": 1.5,
                "tickCount": 10,
                "rugged": False,
                "provablyFair": {"serverSeedHash": "abc123"},
            },
            game_id="20260204-test123",
        )

        await storage.store_event(event)
        games = await storage.get_recent_games(limit=10)
        assert len(games) == 1
        assert games[0]["game_id"] == "20260204-test123"

    @pytest.mark.asyncio
    async def test_store_seed_reveal(self, temp_db):
        """Should capture server seed reveals."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-test456",
                "rugged": True,
                "provablyFair": {
                    "serverSeed": "e9cdaf558aada61213b2ef434ec4e811",
                    "serverSeedHash": "8cc2bab9e7fa24d16fce964233a25ac2",
                },
            },
            game_id="20260204-test456",
        )

        await storage.store_event(event)
        seeds = await storage.get_seed_reveals(limit=10)
        assert len(seeds) == 1
        assert seeds[0]["server_seed"] == "e9cdaf558aada61213b2ef434ec4e811"

    @pytest.mark.asyncio
    async def test_export_for_prng(self, temp_db):
        """Should export data in PRNG attack format."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        # Store a complete game with seed
        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-prng1",
                "rugged": True,
                "price": 2.5,
                "tickCount": 150,
                "provablyFair": {
                    "serverSeed": "abc123def456",
                },
            },
            game_id="20260204-prng1",
            timestamp=datetime(2026, 2, 4, 12, 0, 0),
        )
        await storage.store_event(event)

        export = await storage.export_for_prng()
        assert len(export) == 1
        assert export[0]["game_id"] == "20260204-prng1"
        assert export[0]["server_seed"] == "abc123def456"
        assert "timestamp_ms" in export[0]
