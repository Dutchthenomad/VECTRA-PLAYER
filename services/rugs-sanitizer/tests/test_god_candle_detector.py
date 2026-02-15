"""Tests for god candle change-detection logic."""

from src.god_candle_detector import GodCandleDetector
from src.models import DailyRecords, GodCandleTier


def make_daily_with_gc(game_id: str = "gc-game-1", multiplier: float = 15.5) -> DailyRecords:
    """Create a DailyRecords with a 2x god candle."""
    return DailyRecords(
        highest_today=1122.278,
        god_candle_2x=GodCandleTier(
            multiplier=multiplier,
            timestamp=999,
            game_id=game_id,
            server_seed="seed1",
            massive_jump=[10.0, multiplier],
        ),
    )


def make_daily_no_gc() -> DailyRecords:
    """Create a DailyRecords with no god candle data."""
    return DailyRecords(highest_today=55.3)


def make_daily_multi_tier(
    gc_2x_game: str = "gc-2x",
    gc_50x_game: str = "gc-50x",
) -> DailyRecords:
    """Create a DailyRecords with god candles in 2x and 50x tiers."""
    return DailyRecords(
        highest_today=1500.0,
        god_candle_2x=GodCandleTier(
            multiplier=15.5,
            game_id=gc_2x_game,
            timestamp=100,
        ),
        god_candle_50x=GodCandleTier(
            multiplier=1122.278,
            game_id=gc_50x_game,
            timestamp=200,
        ),
    )


class TestNewDetection:
    """First encounter with a god candle should flag as new."""

    def test_first_god_candle_returns_true(self):
        detector = GodCandleDetector()
        assert detector.check(make_daily_with_gc("game-A")) is True

    def test_new_game_id_returns_true(self):
        detector = GodCandleDetector()
        detector.check(make_daily_with_gc("game-A"))
        assert detector.check(make_daily_with_gc("game-B")) is True


class TestStaleDetection:
    """Repeated god candle data (same game ID) should NOT re-flag."""

    def test_same_id_second_time_returns_false(self):
        detector = GodCandleDetector()
        assert detector.check(make_daily_with_gc("game-A")) is True
        assert detector.check(make_daily_with_gc("game-A")) is False

    def test_same_id_many_times_returns_false(self):
        """Simulates the wire re-reporting stale data on every transition tick."""
        detector = GodCandleDetector()
        detector.check(make_daily_with_gc("game-A"))
        for _ in range(20):
            assert detector.check(make_daily_with_gc("game-A")) is False


class TestMultipleTiers:
    """God candle data may span multiple tiers (2x, 10x, 50x)."""

    def test_multi_tier_first_time(self):
        detector = GodCandleDetector()
        daily = make_daily_multi_tier("gc-2x", "gc-50x")
        assert detector.check(daily) is True

    def test_multi_tier_stale(self):
        detector = GodCandleDetector()
        daily = make_daily_multi_tier("gc-2x", "gc-50x")
        detector.check(daily)
        assert detector.check(daily) is False

    def test_one_new_tier_among_stale(self):
        """If 2x is already seen but 50x is new, should flag."""
        detector = GodCandleDetector()
        # First: only 2x
        detector.check(make_daily_with_gc("gc-2x"))
        # Now: 2x (stale) + 50x (new)
        daily = make_daily_multi_tier("gc-2x", "gc-50x-new")
        assert detector.check(daily) is True

    def test_both_tiers_already_seen(self):
        detector = GodCandleDetector()
        daily = make_daily_multi_tier("gc-2x", "gc-50x")
        detector.check(daily)
        # Same tiers, same IDs
        assert detector.check(make_daily_multi_tier("gc-2x", "gc-50x")) is False


class TestNoGodCandle:
    """No god candle data should never flag."""

    def test_none_input(self):
        detector = GodCandleDetector()
        assert detector.check(None) is False

    def test_no_gc_in_daily(self):
        detector = GodCandleDetector()
        assert detector.check(make_daily_no_gc()) is False


class TestStats:
    def test_initial_stats(self):
        detector = GodCandleDetector()
        stats = detector.get_stats()
        assert stats["new_detections"] == 0
        assert stats["tracked_game_ids"] == 0

    def test_stats_after_detections(self):
        detector = GodCandleDetector()
        detector.check(make_daily_with_gc("game-A"))
        detector.check(make_daily_with_gc("game-A"))  # stale
        detector.check(make_daily_with_gc("game-B"))

        stats = detector.get_stats()
        assert stats["new_detections"] == 2
        assert stats["tracked_game_ids"] == 2

    def test_multi_tier_counts_as_one_detection(self):
        detector = GodCandleDetector()
        daily = make_daily_multi_tier("gc-2x", "gc-50x")
        detector.check(daily)

        stats = detector.get_stats()
        assert stats["new_detections"] == 1
        assert stats["tracked_game_ids"] == 2  # Two distinct game IDs
