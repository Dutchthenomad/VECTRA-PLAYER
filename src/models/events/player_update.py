"""
PlayerUpdate Event Schema - Issue #2

Personal state sync event sent after server-side trades.
This is the server-authoritative source of truth for player balance and positions.

Socket.IO Format: 42["playerUpdate", {...}]
Auth Required: YES - Only sent to authenticated clients

CRITICAL: This event contains the TRUE wallet balance. Local calculations
should be VERIFIED against this event, not trusted independently.

Schema Version: 1.0.0
GitHub Issue: #2
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PlayerUpdate(BaseModel):
    """
    Personal state sync event - server-authoritative truth.

    Sent after each server-side trade to sync local state with server.
    Use this to VERIFY local calculations, not as a secondary source.

    Socket.IO Format: 42["playerUpdate", {...}]
    Auth Required: YES

    Example payload:
    {
        "cash": 3.967072345,
        "cumulativePnL": 0.264879755,
        "positionQty": 0.2222919,
        "avgCost": 1.259605046,
        "totalInvested": 0.251352892
    }
    """

    # ==========================================================================
    # SERVER-AUTHORITATIVE STATE
    # ==========================================================================
    cash: Decimal = Field(..., description="TRUE wallet balance (SOL)")
    cumulativePnL: Decimal = Field(0, description="Total PnL this game (SOL)")
    positionQty: Decimal = Field(0, description="Current position size (units)")
    avgCost: Decimal = Field(0, description="Average entry price")
    totalInvested: Decimal = Field(0, description="Total SOL invested this game")

    # ==========================================================================
    # INGESTION METADATA (added by VECTRA-PLAYER, not from socket)
    # ==========================================================================
    meta_ts: Optional[datetime] = Field(None, description="Ingestion timestamp (UTC)")
    meta_seq: Optional[int] = Field(None, description="Sequence number within session")
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None, description="Event source")
    meta_session_id: Optional[str] = Field(None, description="Recording session UUID")
    meta_game_id: Optional[str] = Field(None, description="Game ID (from context)")
    meta_player_id: Optional[str] = Field(None, description="Player ID (from usernameStatus)")

    @field_validator('cash', 'cumulativePnL', 'positionQty', 'avgCost', 'totalInvested', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        """Coerce float to Decimal for money precision."""
        if v is None:
            return Decimal(0)
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        """Pydantic model configuration."""
        extra = 'allow'
        use_enum_values = True

    @property
    def has_position(self) -> bool:
        """True if player has an open position."""
        return self.positionQty > 0

    @property
    def is_profitable(self) -> bool:
        """True if cumulative PnL is positive."""
        return self.cumulativePnL > 0

    def validate_against_local(
        self,
        local_balance: Decimal,
        local_position: Decimal,
        tolerance: Decimal = Decimal("0.000001"),
    ) -> dict:
        """
        Compare server state against local calculations.

        Args:
            local_balance: Locally calculated balance
            local_position: Locally calculated position size
            tolerance: Maximum acceptable drift

        Returns:
            Dict with 'valid' bool and 'drift' details
        """
        balance_drift = abs(self.cash - local_balance)
        position_drift = abs(self.positionQty - local_position)

        return {
            'valid': balance_drift <= tolerance and position_drift <= tolerance,
            'balance_drift': balance_drift,
            'position_drift': position_drift,
            'server_balance': self.cash,
            'local_balance': local_balance,
            'server_position': self.positionQty,
            'local_position': local_position,
        }
