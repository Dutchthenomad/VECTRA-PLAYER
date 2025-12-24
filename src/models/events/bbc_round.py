"""
BBC Round Placeholder Models - Schema v2.0.0

Placeholder models for BBC sidegame rounds (schema TBD).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, field_validator


class BBCPrediction(str, Enum):
    """Prediction choices for BBC sidegame."""

    BULL = "BULL"
    BEAR = "BEAR"
    CRAB = "CRAB"


class BBCRound(BaseModel):
    """Placeholder schema for a BBC round."""

    round_id: str
    game_id: str
    session_id: str
    start_tick: int
    end_tick: int
    duration_ticks: int
    our_prediction: BBCPrediction | None = None
    our_bet_amount: Decimal | None = None
    actual_result: BBCPrediction | None = None
    won: bool | None = None
    payout: Decimal | None = None
    prediction_ts: int | None = None
    result_ts: int | None = None
    price_at_start: Decimal | None = None
    price_at_end: Decimal | None = None
    volatility_during: Decimal | None = None

    @field_validator(
        "our_bet_amount",
        "payout",
        "price_at_start",
        "price_at_end",
        "volatility_during",
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
