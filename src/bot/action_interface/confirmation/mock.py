"""
MockConfirmationMonitor - Instant confirmation for training mode.

Simulates server confirmation without waiting for actual events.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.action_interface.types import ActionResult, ActionType
    from models.events.player_action import PlayerState


class MockConfirmationMonitor:
    """
    Mock confirmation monitor for training/testing.

    Instantly confirms actions without waiting for server events.
    Useful for RL training where we simulate environment dynamics.
    """

    def __init__(self, simulated_latency_ms: int = 50):
        """
        Initialize mock monitor.

        Args:
            simulated_latency_ms: Simulated latency for confirmed_ts
        """
        self._simulated_latency_ms = simulated_latency_ms

    def instant_confirm(
        self,
        action_id: str,
        action_type: ActionType,
        state_before: PlayerState | None = None,
        state_after: PlayerState | None = None,
        success: bool = True,
        executed_price: Decimal | None = None,
        executed_amount: Decimal | None = None,
        error: str | None = None,
    ) -> ActionResult:
        """
        Instantly confirm an action without waiting for server.

        Args:
            action_id: Unique action identifier
            action_type: Type of action
            state_before: Player state before action
            state_after: Player state after action
            success: Whether action succeeded
            executed_price: Price at execution (optional)
            executed_amount: Amount executed (optional)
            error: Error message if failed (optional)

        Returns:
            ActionResult with simulated timestamps
        """
        # Import here to avoid circular dependency
        from bot.action_interface.types import ActionResult

        # Current timestamp
        client_ts = int(time.time() * 1000)

        # Simulate server timestamps
        server_ts = client_ts + (self._simulated_latency_ms // 2)
        confirmed_ts = client_ts + self._simulated_latency_ms

        return ActionResult(
            success=success,
            action_id=action_id,
            action_type=action_type,
            client_ts=client_ts,
            server_ts=server_ts,
            confirmed_ts=confirmed_ts,
            executed_price=executed_price,
            executed_amount=executed_amount,
            error=error,
            state_before=state_before,
            state_after=state_after,
        )

    def get_latency_stats(self) -> dict[str, float | int]:
        """
        Get simulated latency statistics.

        Returns:
            dict with constant simulated latency
        """
        return {
            "avg_ms": float(self._simulated_latency_ms),
            "min_ms": self._simulated_latency_ms,
            "max_ms": self._simulated_latency_ms,
            "count": 0,  # No actual samples in mock
        }
