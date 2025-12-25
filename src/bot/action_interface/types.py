"""
BotActionInterface type definitions.

Extends (not duplicates) existing Schema v2.0.0 types from models/events/player_action.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.events.player_action import PlayerState

# Re-export ActionType from existing schema for convenience
from models.events.player_action import ActionType, PlayerState


class ExecutionMode(str, Enum):
    """Execution mode for BotActionInterface."""

    RECORDING = "recording"  # Human plays, we record inputs
    TRAINING = "training"  # Fast simulated execution for RL
    VALIDATION = "validation"  # Replay model decisions on recorded games
    LIVE = "live"  # Real browser automation


@dataclass
class GameContext:
    """Game context snapshot at action time."""

    game_id: str
    tick: int
    price: Decimal
    phase: str
    is_active: bool
    connected_players: int = 0


@dataclass
class ActionParams:
    """Input parameters for execute()."""

    action_type: ActionType
    amount: Decimal | None = None
    percentage: Decimal | None = None  # For SELL partial (0.1, 0.25, 0.5, 1.0)
    button: str | None = None  # Raw button text for BET_INCREMENT


@dataclass
class ActionResult:
    """
    Output from execute() with full context for training/persistence.

    Converts to PlayerAction model for EventStore storage.
    """

    success: bool
    action_id: str
    action_type: ActionType

    # Timestamps for latency tracking (ms since epoch)
    client_ts: int = field(default_factory=lambda: int(time.time() * 1000))
    server_ts: int | None = None
    confirmed_ts: int | None = None

    # Execution outcome
    executed_price: Decimal | None = None
    executed_amount: Decimal | None = None
    error: str | None = None

    # State tracking for RL reward calculation
    state_before: PlayerState | None = None
    state_after: PlayerState | None = None

    # Game context at action time
    game_context: GameContext | None = None

    @property
    def send_latency_ms(self) -> int | None:
        """Latency from client send to server receipt."""
        if self.server_ts is not None and self.client_ts is not None:
            return self.server_ts - self.client_ts
        return None

    @property
    def confirm_latency_ms(self) -> int | None:
        """Latency from server receipt to confirmation."""
        if self.confirmed_ts is not None and self.server_ts is not None:
            return self.confirmed_ts - self.server_ts
        return None

    @property
    def total_latency_ms(self) -> int | None:
        """Total latency from client send to confirmation."""
        if self.confirmed_ts is not None and self.client_ts is not None:
            return self.confirmed_ts - self.client_ts
        return None

    @property
    def reward(self) -> Decimal:
        """
        Calculate reward for RL training.

        Reward = change in cumulative PnL from before to after action.
        """
        if self.state_before is not None and self.state_after is not None:
            return self.state_after.cumulative_pnl - self.state_before.cumulative_pnl
        return Decimal("0")
