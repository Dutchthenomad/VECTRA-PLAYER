"""
Short Position State Models - Schema v2.0.0

Placeholder model for tracking short position state.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_validator


class ShortPositionState(BaseModel):
    """Short position state snapshot."""

    has_short: bool
    short_qty: Decimal
    short_entry_price: Decimal
    short_pnl: Decimal
    liquidation_price: Decimal | None = None
    margin_ratio: Decimal | None = None
    at_risk: bool = False

    @field_validator(
        "short_qty",
        "short_entry_price",
        "short_pnl",
        "liquidation_price",
        "margin_ratio",
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

        extra = "allow"
