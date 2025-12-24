"""
ML Episode Event Models - Schema v2.0.0

Defines a summarized episode for training and analysis.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator


class MLEpisode(BaseModel):
    """Aggregated episode summary for ML training."""

    episode_id: str
    session_id: str
    game_id: str
    player_id: str
    started_at: int
    ended_at: int
    duration_ticks: int
    duration_ms: int
    outcome: Literal["rug", "exit_profit", "exit_loss", "timeout"]
    final_pnl: Decimal
    peak_pnl: Decimal
    max_drawdown: Decimal
    total_actions: int
    buy_count: int
    sell_count: int
    avg_position_size: Decimal
    first_buy_tick: int | None = None
    last_sell_tick: int | None = None
    avg_hold_time_ticks: int
    total_reward: Decimal
    avg_reward_per_step: Decimal

    @field_validator(
        "final_pnl",
        "peak_pnl",
        "max_drawdown",
        "avg_position_size",
        "total_reward",
        "avg_reward_per_step",
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
