"""
PlayerLeaderboardPosition Event Schema - Issue #4

Player's current leaderboard standing, sent once on connection.
Secondary authentication confirmation after usernameStatus.

Socket.IO Format: 42["playerLeaderboardPosition", {trace}, {...}]
Auth Required: YES - Only sent to authenticated clients

Schema Version: 1.0.0
GitHub Issue: #4
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LeaderboardPlayerEntry(BaseModel):
    """Player entry in surrounding entries array."""

    playerId: str = Field(..., description="Player's Privy DID")
    username: str | None = Field(None, description="Display name")
    pnl: Decimal = Field(0, description="Period PnL (SOL)")

    @field_validator("pnl", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return Decimal(0)
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class PlayerLeaderboardPosition(BaseModel):
    """
    Player's leaderboard position event.

    Sent once on connection to show player's competitive standing.
    Use to display rank and track improvement over time.

    Socket.IO Format: 42["playerLeaderboardPosition", {trace}, {...}]
    Auth Required: YES

    Example payload:
    {
        "success": true,
        "period": "7d",
        "sortDirection": "highest",
        "playerFound": true,
        "rank": 1164,
        "total": 2595,
        "playerEntry": {
            "playerId": "did:privy:cmaibr7rt0094jp0mc2mbpfu4",
            "username": "Dutch",
            "pnl": -0.015559657
        },
        "surroundingEntries": [...]
    }
    """

    # ==========================================================================
    # QUERY STATUS
    # ==========================================================================
    success: bool = Field(..., description="Query successful")
    period: str = Field("7d", description="Leaderboard period (e.g., '7d')")
    sortDirection: str = Field("highest", description="Sort order")
    playerFound: bool = Field(False, description="Player on leaderboard")

    # ==========================================================================
    # RANK DATA
    # ==========================================================================
    rank: int | None = Field(None, description="Current rank position")
    total: int | None = Field(None, description="Total players on leaderboard")
    playerEntry: LeaderboardPlayerEntry | None = Field(None, description="Player's entry")
    surroundingEntries: list[LeaderboardPlayerEntry] = Field(
        default_factory=list, description="Nearby players"
    )

    # ==========================================================================
    # INGESTION METADATA
    # ==========================================================================
    meta_ts: datetime | None = Field(None, description="Ingestion timestamp (UTC)")
    meta_seq: int | None = Field(None, description="Sequence number within session")
    meta_source: Literal["cdp", "public_ws", "replay", "ui"] | None = Field(
        None, description="Event source"
    )
    meta_session_id: str | None = Field(None, description="Recording session UUID")

    class Config:
        extra = "allow"
        use_enum_values = True

    @property
    def percentile(self) -> float | None:
        """Calculate player's percentile ranking."""
        if self.rank and self.total and self.total > 0:
            return (1 - (self.rank / self.total)) * 100
        return None
