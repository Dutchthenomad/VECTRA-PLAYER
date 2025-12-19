"""
GameState Characterization Tests - AUDIT FIX Edge Cases

Documents and tests the specific behaviors fixed by AUDIT FIX patches.
These tests capture existing behavior as a safety net for refactoring.

DO NOT modify expected values to make tests pass.

AUDIT FIX Summary (from src/core/game_state.py):
1. Bounded history using deque with maxlen (prevents unbounded memory growth)
2. Transaction log bounded with auto-eviction
3. Closed positions history bounded with auto-eviction
4. Removed duplicate total_pnl tracking
"""

from collections import deque
from decimal import Decimal

import pytest

from core.game_state import (
    MAX_CLOSED_POSITIONS_SIZE,
    MAX_HISTORY_SIZE,
    MAX_TRANSACTION_LOG_SIZE,
    GameState,
    StateSnapshot,
)


class TestAuditFixBoundedHistory:
    """
    AUDIT FIX: Bounded history to prevent unbounded memory growth.

    Uses deque with maxlen for O(1) bounded memory.
    """

    def test_history_uses_deque_with_maxlen(self):
        """
        Document: History is a deque with configurable maxlen.

        AUDIT FIX: Use deque with maxlen for O(1) bounded memory
        """
        state = GameState()

        # History should be a deque
        assert isinstance(state._history, deque)

        # Should have maxlen set
        assert state._history.maxlen == MAX_HISTORY_SIZE

    def test_history_auto_evicts_old_entries(self):
        """
        Document: When history exceeds maxlen, oldest entries are evicted.

        AUDIT FIX: deque auto-evicts when maxlen reached
        """
        # Use a small maxlen for testing
        state = GameState()
        original_maxlen = state._history.maxlen

        # Create a new deque with small maxlen for testing
        state._history = deque(maxlen=5)

        # Add more entries than maxlen
        for i in range(10):
            state._history.append(
                StateSnapshot(
                    timestamp=None,
                    tick=i,
                    balance=Decimal("1.0"),
                )
            )

        # Should only have last 5 entries
        assert len(state._history) == 5

        # Oldest entry should be tick 5 (not 0)
        assert state._history[0].tick == 5

        # Newest entry should be tick 9
        assert state._history[-1].tick == 9

    def test_transaction_log_bounded(self):
        """
        Document: Transaction log is bounded with auto-eviction.

        AUDIT FIX: bounded transaction log
        """
        state = GameState()

        assert isinstance(state._transaction_log, deque)
        assert state._transaction_log.maxlen == MAX_TRANSACTION_LOG_SIZE

    def test_closed_positions_bounded(self):
        """
        Document: Closed positions history is bounded.

        AUDIT FIX: deque auto-evicts when maxlen reached
        """
        state = GameState()

        assert isinstance(state._closed_positions, deque)
        assert state._closed_positions.maxlen == MAX_CLOSED_POSITIONS_SIZE


class TestAuditFixMemoryConstants:
    """
    Test configurable memory limits.
    """

    def test_max_history_size_from_config(self):
        """
        Document: MAX_HISTORY_SIZE is configurable via config.

        AUDIT FIX: Bounded history to prevent unbounded memory growth
        """
        # Should be a reasonable default
        assert MAX_HISTORY_SIZE >= 100
        assert MAX_HISTORY_SIZE <= 100000

    def test_max_transaction_log_size(self):
        """Document: Transaction log has fixed size limit."""
        assert MAX_TRANSACTION_LOG_SIZE == 1000

    def test_max_closed_positions_size(self):
        """Document: Closed positions has fixed size limit."""
        assert MAX_CLOSED_POSITIONS_SIZE == 500


class TestAuditFixGetHistoryMethods:
    """
    Test that get_history methods work correctly with deque.
    """

    def test_get_history_returns_list(self):
        """
        Document: get_history() converts deque to list for callers.

        AUDIT FIX: works with deque
        """
        state = GameState()

        # Add some history
        state._history.append(
            StateSnapshot(
                timestamp=None,
                tick=1,
                balance=Decimal("1.0"),
            )
        )

        history = state.get_history()

        # Should return a list (not deque) for compatibility
        assert isinstance(history, list)
        assert len(history) == 1

    def test_get_transaction_log_returns_list(self):
        """
        Document: get_transaction_log() converts deque to list.

        AUDIT FIX: works with deque
        """
        state = GameState()

        # Add a transaction
        state._transaction_log.append({"type": "test", "amount": Decimal("0.01")})

        log = state.get_transaction_log()

        assert isinstance(log, list)
        assert len(log) == 1


class TestGameStateThreadSafety:
    """
    Test thread safety of GameState operations.
    """

    def test_has_reentrant_lock(self):
        """Document: GameState uses RLock for thread safety."""
        import threading

        state = GameState()

        assert isinstance(state._lock, type(threading.RLock()))

    def test_lock_is_used_in_state_access(self):
        """
        Document: State modifications should be thread-safe.

        This test verifies that concurrent updates don't cause corruption.
        """
        import concurrent.futures
        import random

        state = GameState(initial_balance=Decimal("10.0"))

        def update_balance():
            for _ in range(100):
                # Random balance updates
                amount = Decimal(str(random.uniform(-0.1, 0.1)))
                state.update_balance(amount, f"test_{random.randint(0, 1000)}")

        # Run concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(update_balance) for _ in range(4)]
            concurrent.futures.wait(futures)

        # Should not crash - balance should be a valid Decimal
        balance = state.get("balance")
        assert isinstance(balance, Decimal)


class TestGameStateStatistics:
    """
    Test statistics tracking behavior.
    """

    def test_stats_not_duplicated(self):
        """
        Document: Statistics should not have duplicate tracking.

        AUDIT FIX: removed duplicate total_pnl update
        """
        state = GameState(initial_balance=Decimal("1.0"))

        initial_stats = state.get_stats()

        # total_pnl should start at 0
        assert initial_stats["total_pnl"] == Decimal("0")

        # Update balance with a gain
        state.update_balance(Decimal("0.1"), "test_win")

        # total_pnl should be updated only once
        # (not duplicated in multiple places)
        updated_stats = state.get_stats()
        assert updated_stats["total_pnl"] == Decimal("0.1")

    def test_stats_track_all_expected_fields(self):
        """Document: Stats should track all expected fields."""
        state = GameState()
        stats = state.get_stats()

        expected_fields = [
            "total_trades",
            "winning_trades",
            "losing_trades",
            "total_pnl",
            "max_drawdown",
            "peak_balance",
            "sidebets_won",
            "sidebets_lost",
            "games_played",
        ]

        for field in expected_fields:
            assert field in stats, f"Missing stat field: {field}"
