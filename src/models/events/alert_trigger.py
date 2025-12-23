"""
Alert Trigger Event Models - Schema v2.0.0

Defines alert types and alert trigger payloads for UI/system notifications.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class AlertType(str, Enum):
    """All supported alert trigger types."""

    # Trade
    TRADE_SUCCESS = "TRADE_SUCCESS"
    TRADE_FAILED = "TRADE_FAILED"

    # Position
    POSITION_PROFIT = "POSITION_PROFIT"
    POSITION_LOSS = "POSITION_LOSS"
    SIDEBET_WON = "SIDEBET_WON"
    SIDEBET_LOST = "SIDEBET_LOST"

    # Game
    GAME_START = "GAME_START"
    GAME_RUG = "GAME_RUG"
    MULTIPLIER_MILESTONE = "MULTIPLIER_MILESTONE"

    # Volatility/Timing
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    VOLATILITY_CALM = "VOLATILITY_CALM"
    SIDEBET_OPTIMAL_ZONE = "SIDEBET_OPTIMAL_ZONE"
    HIGH_POTENTIAL_ENTRY = "HIGH_POTENTIAL_ENTRY"
    HIGH_POTENTIAL_EXIT = "HIGH_POTENTIAL_EXIT"
    RUG_WARNING = "RUG_WARNING"
    SURVIVAL_MILESTONE = "SURVIVAL_MILESTONE"

    # Player Patterns
    EXCEPTIONAL_PLAYER_ENTRY = "EXCEPTIONAL_PLAYER_ENTRY"
    EXCEPTIONAL_PLAYER_EXIT = "EXCEPTIONAL_PLAYER_EXIT"
    CUSTOM_SIGNAL_1 = "CUSTOM_SIGNAL_1"
    CUSTOM_SIGNAL_2 = "CUSTOM_SIGNAL_2"
    CUSTOM_SIGNAL_3 = "CUSTOM_SIGNAL_3"

    # Short
    SHORT_ENTRY_SIGNAL = "SHORT_ENTRY_SIGNAL"
    SHORT_EXIT_SIGNAL = "SHORT_EXIT_SIGNAL"
    SHORT_LIQUIDATION_WARNING = "SHORT_LIQUIDATION_WARNING"

    # Sidegames
    BBC_ROUND_START = "BBC_ROUND_START"
    BBC_OPTIMAL_PREDICTION = "BBC_OPTIMAL_PREDICTION"
    CANDLEFLIP_START = "CANDLEFLIP_START"
    CANDLEFLIP_STREAK = "CANDLEFLIP_STREAK"

    # System
    CONNECTION_LOST = "CONNECTION_LOST"
    CONNECTION_RESTORED = "CONNECTION_RESTORED"
    LATENCY_WARNING = "LATENCY_WARNING"


class AlertTrigger(BaseModel):
    """Alert triggered by system, trade, or game events."""

    alert_id: str
    alert_type: AlertType
    severity: Literal["info", "success", "warning", "error"]
    triggered_at: int
    expires_at: int | None = None
    game_id: str | None = None
    player_id: str | None = None
    title: str
    message: str
    source_event: str | None = None
    source_data: dict[str, Any] | None = None
    can_dismiss: bool = True
    sound_enabled: bool = True
    priority: int = 0

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        extra = "allow"
