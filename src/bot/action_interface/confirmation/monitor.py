"""
ConfirmationMonitor - Tracks action confirmations and measures latency.

Subscribes to EventBus PLAYER_UPDATE events and correlates them with
pending actions to measure round-trip latency.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.action_interface.types import ActionResult, ActionType
    from models.events.player_action import PlayerState
    from services.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class PendingAction:
    """Tracks an action awaiting server confirmation."""

    action_id: str
    action_type: ActionType
    client_ts: int
    state_before: PlayerState | None
    callback: Callable[[ActionResult], None] | None = None


class ConfirmationMonitor:
    """
    Monitors PLAYER_UPDATE events to confirm actions and measure latency.

    Uses FIFO matching: assumes server confirms actions in the order they
    were sent. Maintains rolling latency statistics.
    """

    def __init__(
        self,
        event_bus: EventBus,
        max_pending: int = 100,
        latency_window: int = 100,
    ):
        """
        Initialize the confirmation monitor.

        Args:
            event_bus: EventBus instance to subscribe to
            max_pending: Maximum pending actions to track
            latency_window: Number of latency samples to keep for stats
        """
        self._event_bus = event_bus
        self._max_pending = max_pending
        self._latency_window = latency_window

        # Thread-safe data structures
        self._lock = threading.RLock()
        self._pending: deque[PendingAction] = deque(maxlen=max_pending)
        self._latency_samples: deque[int] = deque(maxlen=latency_window)

        # Subscription tracking
        self._subscribed = False

    def start(self):
        """Start monitoring by subscribing to PLAYER_UPDATE events."""
        with self._lock:
            if self._subscribed:
                logger.warning("ConfirmationMonitor already started")
                return

            # Import here to avoid circular dependency
            from services.event_bus import Events

            self._event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update, weak=False)
            self._subscribed = True
            logger.info("ConfirmationMonitor started")

    def stop(self):
        """Stop monitoring by unsubscribing from events."""
        with self._lock:
            if not self._subscribed:
                logger.warning("ConfirmationMonitor not started")
                return

            # Import here to avoid circular dependency
            from services.event_bus import Events

            self._event_bus.unsubscribe(Events.PLAYER_UPDATE, self._on_player_update)
            self._subscribed = False

            # Clear pending actions
            pending_count = len(self._pending)
            self._pending.clear()

            if pending_count > 0:
                logger.warning(
                    f"ConfirmationMonitor stopped with {pending_count} unconfirmed actions"
                )

            logger.info("ConfirmationMonitor stopped")

    def register_pending(
        self,
        action_id: str,
        action_type: ActionType,
        state_before: PlayerState | None = None,
        callback: Callable[[ActionResult], None] | None = None,
    ):
        """
        Register a pending action awaiting confirmation.

        Args:
            action_id: Unique action identifier
            action_type: Type of action
            state_before: Player state before action
            callback: Optional callback to invoke on confirmation
        """
        with self._lock:
            client_ts = int(time.time() * 1000)

            pending = PendingAction(
                action_id=action_id,
                action_type=action_type,
                client_ts=client_ts,
                state_before=state_before,
                callback=callback,
            )

            self._pending.append(pending)

            logger.debug(
                f"Registered pending action {action_id} ({action_type}), "
                f"queue depth: {len(self._pending)}"
            )

    def get_latency_stats(self) -> dict[str, float | int]:
        """
        Get latency statistics from recent confirmations.

        Returns:
            dict with avg, min, max latency (ms) and sample count
        """
        with self._lock:
            if not self._latency_samples:
                return {
                    "avg_ms": 0.0,
                    "min_ms": 0,
                    "max_ms": 0,
                    "count": 0,
                }

            samples = list(self._latency_samples)
            return {
                "avg_ms": sum(samples) / len(samples),
                "min_ms": min(samples),
                "max_ms": max(samples),
                "count": len(samples),
            }

    def _on_player_update(self, event: dict):
        """
        Handle PLAYER_UPDATE event from EventBus.

        Args:
            event: Event dict with 'name' and 'data' keys
        """
        with self._lock:
            if not self._pending:
                # No pending actions to confirm
                return

            # Extract event data
            data = event.get("data", event)
            confirmed_ts = int(time.time() * 1000)

            # Extract player state from event data
            state_after = self._extract_player_state(data)

            # FIFO matching: confirm oldest pending action
            pending = self._pending.popleft()

            # Calculate latency
            latency = confirmed_ts - pending.client_ts
            self._latency_samples.append(latency)

            logger.debug(
                f"Confirmed action {pending.action_id} ({pending.action_type}), "
                f"latency: {latency}ms"
            )

            # Build ActionResult
            result = self._build_action_result(
                pending=pending,
                confirmed_ts=confirmed_ts,
                state_after=state_after,
            )

            # Invoke callback if provided
            if pending.callback:
                try:
                    pending.callback(result)
                except Exception as e:
                    logger.error(
                        f"Error in confirmation callback for {pending.action_id}: {e}",
                        exc_info=True,
                    )

    def _extract_player_state(self, data: dict) -> PlayerState | None:
        """
        Extract PlayerState from PLAYER_UPDATE event data.

        Args:
            data: Event data dict

        Returns:
            PlayerState instance or None if extraction fails
        """
        try:
            # Import here to avoid circular dependency
            from models.events.player_action import PlayerState

            # Extract financial fields from playerUpdate event
            # Server-authoritative state comes in this structure:
            # {
            #   "walletAddress": "...",
            #   "currentBalance": 123.45,
            #   "position": {
            #       "qty": 10,
            #       "avgCost": 1.5,
            #       "totalInvested": 15.0
            #   },
            #   "cumulativePnl": 5.0
            # }

            balance = data.get("currentBalance", 0)
            position = data.get("position", {})

            return PlayerState(
                cash=Decimal(str(balance)),
                position_qty=Decimal(str(position.get("qty", 0))),
                avg_cost=Decimal(str(position.get("avgCost", 0))),
                total_invested=Decimal(str(position.get("totalInvested", 0))),
                cumulative_pnl=Decimal(str(data.get("cumulativePnl", 0))),
            )
        except Exception as e:
            logger.warning(f"Failed to extract PlayerState from event data: {e}")
            return None

    def _build_action_result(
        self,
        pending: PendingAction,
        confirmed_ts: int,
        state_after: PlayerState | None,
    ) -> ActionResult:
        """
        Build ActionResult from confirmed action.

        Args:
            pending: Pending action that was confirmed
            confirmed_ts: Confirmation timestamp
            state_after: Player state after action

        Returns:
            ActionResult instance
        """
        # Import here to avoid circular dependency
        from bot.action_interface.types import ActionResult

        return ActionResult(
            success=True,
            action_id=pending.action_id,
            action_type=pending.action_type,
            client_ts=pending.client_ts,
            server_ts=None,  # Not tracked by monitor (would need WS interception)
            confirmed_ts=confirmed_ts,
            state_before=pending.state_before,
            state_after=state_after,
        )
