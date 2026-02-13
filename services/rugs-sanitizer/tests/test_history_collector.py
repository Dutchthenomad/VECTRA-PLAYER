"""Tests for smart gameHistory collection strategy."""

from src.history_collector import HistoryCollector


def make_history_entry(game_id: str, peak: float = 3.0) -> dict:
    """Create a raw gameHistory entry."""
    return {
        "id": game_id,
        "timestamp": 1770347058350,
        "peakMultiplier": peak,
        "rugged": True,
        "gameVersion": "v3",
        "prices": [1.0, peak, 0.01],
        "globalTrades": None,
        "globalSidebets": [],
        "provablyFair": {
            "serverSeed": f"seed-{game_id}",
            "serverSeedHash": f"hash-{game_id}",
        },
    }


def make_history_window(start: int, count: int = 10) -> list[dict]:
    """Create a 10-game history window."""
    return [make_history_entry(f"game-{i}") for i in range(start, start + count)]


class TestCollectionInterval:
    """Test the every-N-th-rug collection strategy."""

    def test_collects_on_10th_rug(self):
        collector = HistoryCollector(collection_interval=10)
        records = []

        for i in range(10):
            history = make_history_window(i * 10)
            result = collector.on_rug(history)
            records.extend(result)

        # Should collect once: on the 10th rug
        assert collector.rug_count == 10
        assert len(records) == 10  # 10 games from the window

    def test_no_collection_before_interval(self):
        collector = HistoryCollector(collection_interval=10)

        for i in range(9):
            result = collector.on_rug(make_history_window(i * 10))
            assert result == []

    def test_collects_every_10th(self):
        collector = HistoryCollector(collection_interval=10)
        collection_count = 0

        for i in range(30):
            result = collector.on_rug(make_history_window(i * 10))
            if result:
                collection_count += 1

        assert collection_count == 3

    def test_custom_interval(self):
        collector = HistoryCollector(collection_interval=5)
        collection_count = 0

        for i in range(15):
            result = collector.on_rug(make_history_window(i * 10))
            if result:
                collection_count += 1

        assert collection_count == 3

    def test_next_collection_countdown(self):
        collector = HistoryCollector(collection_interval=10)
        assert collector.next_collection_in == 10

        collector.on_rug(None)  # rug 1
        assert collector.next_collection_in == 9

        for _ in range(8):
            collector.on_rug(None)  # rugs 2-9
        assert collector.next_collection_in == 1


class TestGodCandleOverride:
    """Test that god candle forces immediate collection."""

    def test_god_candle_overrides_interval(self):
        collector = HistoryCollector(collection_interval=10)
        history = make_history_window(0)

        # First rug with god candle — should collect even though not 10th
        result = collector.on_rug(history, has_god_candle=True)
        assert len(result) == 10
        assert collector.rug_count == 1

    def test_god_candle_counted_in_stats(self):
        collector = HistoryCollector(collection_interval=10)
        collector.on_rug(make_history_window(0), has_god_candle=True)

        stats = collector.get_stats()
        assert stats["god_candle_captures"] == 1


class TestDeduplication:
    """Test dedup by gameId safety net."""

    def test_same_ids_deduplicated(self):
        collector = HistoryCollector(collection_interval=1)

        # Same window twice
        history = make_history_window(0)
        result1 = collector.on_rug(history)
        assert len(result1) == 10

        result2 = collector.on_rug(history)
        assert len(result2) == 0  # All already captured

    def test_partially_overlapping_windows(self):
        collector = HistoryCollector(collection_interval=1)

        # First window: games 0-9
        result1 = collector.on_rug(make_history_window(0))
        assert len(result1) == 10

        # Overlapping window: games 5-14 (5 overlap, 5 new)
        result2 = collector.on_rug(make_history_window(5))
        assert len(result2) == 5  # Only games 10-14 are new

    def test_dedup_stats(self):
        collector = HistoryCollector(collection_interval=1)
        collector.on_rug(make_history_window(0))
        collector.on_rug(make_history_window(0))

        stats = collector.get_stats()
        assert stats["duplicates_skipped"] == 10


class TestEdgeCases:
    def test_no_history_data(self):
        collector = HistoryCollector(collection_interval=1)
        result = collector.on_rug(None)
        assert result == []
        assert collector.rug_count == 1

    def test_empty_history(self):
        collector = HistoryCollector(collection_interval=1)
        result = collector.on_rug([])
        assert result == []

    def test_entry_without_id(self):
        collector = HistoryCollector(collection_interval=1)
        result = collector.on_rug([{"timestamp": 123}])
        assert result == []

    def test_stats(self):
        collector = HistoryCollector(collection_interval=5)
        stats = collector.get_stats()
        assert stats["rugs_seen"] == 0
        assert stats["collection_interval"] == 5
        assert stats["next_collection_in"] == 5
