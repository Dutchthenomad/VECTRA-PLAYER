"""
Other Player Event Models - Schema v2.0.0

Captures high-signal actions from other players and exceptional player profiles.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, field_validator

from .player_action import GamePhase


class OtherActionType(str, Enum):
    """Limited action types observed for other players."""

    BUY = "BUY"
    SELL = "SELL"
    SHORT_OPEN = "SHORT_OPEN"
    SHORT_CLOSE = "SHORT_CLOSE"


class OtherPlayerAction(BaseModel):
    """Observed action from another player in the game."""

    session_id: str
    game_id: str
    player_id: str
    username: str | None = None
    action_type: OtherActionType
    amount: Decimal
    price: Decimal
    tick: int
    game_phase: GamePhase
    server_ts: int
    ingested_ts: int
    player_level: int
    player_pnl: Decimal
    player_position: Decimal
    leaderboard_rank: int | None = None
    short_position: Decimal | None = None
    short_entry_price: Decimal | None = None

    @field_validator(
        "amount",
        "price",
        "player_pnl",
        "player_position",
        "short_position",
        "short_entry_price",
        mode="before",
    )
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


class ExceptionalPlayer(BaseModel):
    """Aggregated profile for a high-signal or exceptional player."""

    player_id: str
    username: str | None = None
    total_games_observed: int
    total_trades_observed: int
    win_rate: float
    avg_pnl_per_game: Decimal
    avg_entry_tick: int
    avg_exit_tick: int
    preferred_entry_zone: str | None = None
    avg_hold_duration: int
    is_consistent_winner: bool
    is_imitation_target: bool
    specialization: str | None = None

    @field_validator("avg_pnl_per_game", mode="before")
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
