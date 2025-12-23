"""
Candleflip Placeholder Models - Schema v2.0.0

Placeholder models for Candleflip sidegame rounds (schema TBD).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, field_validator


class CandleflipChoice(str, Enum):
    """Candle color choice for Candleflip."""

    GREEN = "GREEN"
    RED = "RED"


class CandleflipRound(BaseModel):
    """Placeholder schema for a Candleflip round."""

    round_id: str
    game_id: str
    session_id: str
    our_choice: CandleflipChoice | None = None
    our_bet_amount: Decimal | None = None
    result: CandleflipChoice | None = None
    won: bool | None = None
    payout: Decimal | None = None
    current_streak: int | None = None
    streak_direction: CandleflipChoice | None = None
    bet_ts: int | None = None
    result_ts: int | None = None

    @field_validator("our_bet_amount", "payout", mode="before")
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
