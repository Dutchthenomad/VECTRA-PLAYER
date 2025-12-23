"""
Player Action Event Models - Schema v2.0.0

Defines canonical player action events for EventStore.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, field_validator


class ActionType(str, Enum):
    """Supported player action types."""

    BUY = "BUY"
    SELL = "SELL"
    SIDEBET = "SIDEBET"
    SHORT_OPEN = "SHORT_OPEN"
    SHORT_CLOSE = "SHORT_CLOSE"
    BET_INCREMENT = "BET_INCREMENT"
    BET_DECREMENT = "BET_DECREMENT"
    BET_PERCENTAGE = "BET_PERCENTAGE"
    BBC_PREDICT = "BBC_PREDICT"
    CANDLEFLIP_BET = "CANDLEFLIP_BET"


class GamePhase(str, Enum):
    """Game phase at the time of action."""

    COOLDOWN = "COOLDOWN"
    ACTIVE = "ACTIVE"
    RUGGED = "RUGGED"


class GameContext(BaseModel):
    """Snapshot of game context when the action occurred."""

    game_id: str
    tick: int
    price: Decimal
    phase: GamePhase
    is_pre_round: bool
    connected_players: int

    @field_validator("price", mode="before")
    @classmethod
    def _coerce_price(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        extra = "allow"


class PlayerState(BaseModel):
    """Player financial state snapshot before/after an action."""

    cash: Decimal
    position_qty: Decimal
    avg_cost: Decimal
    total_invested: Decimal
    cumulative_pnl: Decimal

    @field_validator(
        "cash",
        "position_qty",
        "avg_cost",
        "total_invested",
        "cumulative_pnl",
        mode="before",
    )
    @classmethod
    def _coerce_decimal(cls, v):
        if v is None:
            return Decimal("0")
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        """Pydantic model configuration."""

        extra = "allow"


class ActionTimestamps(BaseModel):
    """Client/server timestamps for action lifecycle (ms)."""

    client_ts: int
    server_ts: int
    confirmed_ts: int

    @property
    def send_latency_ms(self) -> int:
        """Latency from client send to server receipt."""
        return self.server_ts - self.client_ts

    @property
    def confirm_latency_ms(self) -> int:
        """Latency from server receipt to confirmation."""
        return self.confirmed_ts - self.server_ts

    @property
    def total_latency_ms(self) -> int:
        """Total latency from client send to confirmation."""
        return self.confirmed_ts - self.client_ts

    class Config:
        """Pydantic model configuration."""

        extra = "allow"


class ActionOutcome(BaseModel):
    """Execution result for an action."""

    success: bool
    executed_price: Decimal | None = None
    executed_amount: Decimal | None = None
    fee: Decimal | None = None
    error: str | None = None
    error_reason: str | None = None

    @field_validator("executed_price", "executed_amount", "fee", mode="before")
    @classmethod
    def _coerce_decimal_optional(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        """Pydantic model configuration."""

        extra = "allow"


class PlayerAction(BaseModel):
    """Canonical player action event stored in EventStore."""

    action_id: str
    session_id: str
    game_id: str
    player_id: str
    username: str | None = None
    action_type: ActionType
    button: str | None = None
    amount: Decimal | None = None
    percentage: Decimal | None = None
    game_context: GameContext
    state_before: PlayerState
    timestamps: ActionTimestamps
    outcome: ActionOutcome
    state_after: PlayerState | None = None

    @field_validator("amount", "percentage", mode="before")
    @classmethod
    def _coerce_decimal_optional(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        extra = "allow"
