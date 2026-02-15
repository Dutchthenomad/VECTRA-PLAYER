"""
Tests for RecordingSubscriber.

Tests gameHistory extraction, deduplication, and storage integration.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Mock foundation imports for testing
class MockGameTickEvent:
    """Mock GameTickEvent for testing."""

    def __init__(
        self,
        rugged: bool = False,
        game_history: list | None = None,
        price: float = 1.0,
    ):
        self.type = "game.tick"
        self.ts = int(datetime.utcnow().timestamp() * 1000)
        self.game_id = "test-game-123"
        self.seq = 1
        self.active = not rugged
        self.rugged = rugged
        self.price = price
        self.tick_count = 100
        self.cooldown_timer = 0
        self.allow_pre_round_buys = False
        self.trade_count = 10
        self.phase = "GAME" if not rugged else "COOLDOWN"
        self.game_history = game_history
        self.leaderboard = []


class MockPlayerStateEvent:
    """Mock PlayerStateEvent for testing."""

    def __init__(self):
        self.type = "player.state"
        self.ts = int(datetime.utcnow().timestamp() * 1000)
        self.game_id = "test-game-123"
        self.seq = 1
        self.cash = 100.0
        self.position_qty = 0.0
        self.avg_cost = 0.0
        self.cumulative_pnl = 0.0
        self.total_invested = 0.0


class MockFoundationClient:
    """Mock FoundationClient for testing."""

    def __init__(self):
        self._handlers = {}

    def on(self, event_type: str, callback):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(callback)

        def unsubscribe():
            self._handlers[event_type].remove(callback)

        return unsubscribe

    def is_connected(self):
        return True


# Import the modules we're testing
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Patch foundation imports before importing subscriber
with patch.dict(
    "sys.modules",
    {
        "foundation": MagicMock(),
        "foundation.client": MagicMock(),
        "foundation.events": MagicMock(),
        "foundation.subscriber": MagicMock(),
    },
):
    from src.dedup import DeduplicationTracker
    from src.storage import GameStorage


class TestDeduplicationTracker:
    """Tests for DeduplicationTracker."""

    def test_is_duplicate_returns_false_for_new_id(self):
        """New gameIds should not be duplicates."""
        tracker = DeduplicationTracker()
        assert tracker.is_duplicate("game-1") is False

    def test_is_duplicate_returns_true_after_marking(self):
        """Marked gameIds should be duplicates."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("game-1")
        assert tracker.is_duplicate("game-1") is True

    def test_lru_eviction(self):
        """Old entries should be evicted when cache is full."""
        tracker = DeduplicationTracker(max_cache_size=3)

        # Add 5 items (cache only holds 3)
        for i in range(5):
            tracker.mark_seen(f"game-{i}")

        # First two should be evicted
        assert tracker.is_duplicate("game-0") is False
        assert tracker.is_duplicate("game-1") is False

        # Last three should still be present
        assert tracker.is_duplicate("game-2") is True
        assert tracker.is_duplicate("game-3") is True
        assert tracker.is_duplicate("game-4") is True

    def test_persistence_roundtrip(self):
        """Persisted state should survive reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "dedup.json"

            # Create tracker and add items
            tracker1 = DeduplicationTracker(persist_path=persist_path)
            tracker1.mark_seen("game-a")
            tracker1.mark_seen("game-b")
            tracker1.persist()

            # Create new tracker, should load state
            tracker2 = DeduplicationTracker(persist_path=persist_path)
            assert tracker2.is_duplicate("game-a") is True
            assert tracker2.is_duplicate("game-b") is True
            assert tracker2.is_duplicate("game-c") is False

    def test_clear(self):
        """Clear should remove all entries."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("game-1")
        tracker.mark_seen("game-2")
        tracker.clear()

        assert tracker.is_duplicate("game-1") is False
        assert tracker.is_duplicate("game-2") is False
        assert tracker.get_seen_count() == 0


class TestGameStorage:
    """Tests for GameStorage."""

    def test_store_games_returns_count(self):
        """store_games should return number of games stored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = GameStorage(tmpdir)

            games = [
                {"gameId": "game-1", "tickCount": 100, "price": 1.5},
                {"gameId": "game-2", "tickCount": 200, "price": 2.0},
            ]

            count = storage.store_games(games)
            assert count == 2

    def test_enriches_games_with_metadata(self):
        """Games should be enriched with capture metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = GameStorage(tmpdir)

            games = [{"gameId": "game-1"}]
            storage.store_games(games)

            # Force flush
            storage.flush()

            # Get back the stored game
            recent = storage.get_recent_games(1)
            assert len(recent) == 1

            # Check metadata fields exist
            game = recent[0]
            assert "_captured_at" in game or "_captured_at" in str(game)

    def test_get_storage_stats(self):
        """get_storage_stats should return storage info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = GameStorage(tmpdir)

            stats = storage.get_storage_stats()
            assert "storage_path" in stats
            assert "total_size_bytes" in stats
            assert "parquet_available" in stats

    def test_empty_storage_counts(self):
        """Empty storage should return zero counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = GameStorage(tmpdir)

            assert storage.get_total_game_count() == 0
            assert storage.get_today_game_count() == 0


class TestRecordingIntegration:
    """Integration tests for recording workflow."""

    def test_gamehistory_extraction_workflow(self):
        """Test complete workflow: gameHistory -> dedup -> storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = GameStorage(Path(tmpdir) / "games")
            dedup = DeduplicationTracker()

            # Simulate gameHistory with 3 games
            game_history = [
                {"gameId": "g1", "tickCount": 100, "finalPrice": 1.5},
                {"gameId": "g2", "tickCount": 150, "finalPrice": 2.0},
                {"gameId": "g3", "tickCount": 80, "finalPrice": 1.2},
            ]

            # First pass: all games should be stored
            new_games = []
            for game in game_history:
                if not dedup.is_duplicate(game["gameId"]):
                    dedup.mark_seen(game["gameId"])
                    new_games.append(game)

            stored = storage.store_games(new_games)
            assert stored == 3

            # Second pass: same games should be deduped
            new_games = []
            for game in game_history:
                if not dedup.is_duplicate(game["gameId"]):
                    dedup.mark_seen(game["gameId"])
                    new_games.append(game)

            assert len(new_games) == 0

            # Third pass: mix of new and old
            game_history_2 = [
                {"gameId": "g2", "tickCount": 150, "finalPrice": 2.0},  # duplicate
                {"gameId": "g4", "tickCount": 200, "finalPrice": 3.0},  # new
            ]

            new_games = []
            for game in game_history_2:
                if not dedup.is_duplicate(game["gameId"]):
                    dedup.mark_seen(game["gameId"])
                    new_games.append(game)

            assert len(new_games) == 1
            assert new_games[0]["gameId"] == "g4"


class TestRecordingStats:
    """Tests for recording statistics tracking."""

    def test_stats_initialization(self):
        """Stats should initialize with correct defaults."""
        from src.subscriber import RecordingStats

        stats = RecordingStats()
        assert stats.session_games == 0
        assert stats.today_games == 0
        assert stats.total_games == 0
        assert stats.is_recording is True

    def test_stats_to_dict(self):
        """Stats should serialize to dict correctly."""
        from src.subscriber import RecordingStats

        stats = RecordingStats()
        stats.session_games = 5
        stats.total_games = 100

        d = stats.to_dict()
        assert d["session_games"] == 5
        assert d["total_games"] == 100
        assert "session_start" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
