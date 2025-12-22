"""
GameStateUpdate Event Schema - Issue #1

Primary tick event broadcast ~4x/second to all connected clients.
This is the most critical event for game state synchronization.

Socket.IO Format: 42["gameStateUpdate", {...}]
Auth Required: NO - Broadcast to all connections

Schema Version: 1.0.0
GitHub Issue: #1
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# NESTED MODELS
# =============================================================================


class SideBet(BaseModel):
    """Active sidebet for a player."""

    target: int = Field(..., description="Target multiplier (e.g., 10 for 10x)")
    betSize: Decimal = Field(..., description="Bet amount in SOL")
    startTick: int = Field(..., description="Tick when sidebet was placed")
    endTick: int = Field(..., description="Tick when sidebet expires")

    @field_validator("betSize", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        """Coerce float to Decimal for money precision."""
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class ShortPosition(BaseModel):
    """Short position details for a player."""

    amount: Decimal = Field(..., description="Short position size")
    entryPrice: Decimal = Field(..., description="Short entry price")

    @field_validator("amount", "entryPrice", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class LeaderboardEntry(BaseModel):
    """
    Single player entry in the leaderboard array.
    Contains server-authoritative state for position tracking.
    """

    id: str = Field(..., description="Unique player ID (did:privy:*)")
    username: str | None = Field(None, description="Display name (null if not set)")
    level: int = Field(0, description="Player level")

    # PnL fields (server-authoritative)
    pnl: Decimal = Field(..., description="Total PnL this game (SOL)")
    regularPnl: Decimal = Field(0, description="PnL from regular trades")
    sidebetPnl: Decimal = Field(0, description="PnL from sidebets")
    shortPnl: Decimal = Field(0, description="PnL from shorts")
    pnlPercent: Decimal = Field(0, description="PnL as percentage")

    # Position fields (server-authoritative)
    hasActiveTrades: bool = Field(False, description="Has open position")
    positionQty: Decimal = Field(0, description="Position size (units)")
    avgCost: Decimal = Field(0, description="Average entry price")
    totalInvested: Decimal = Field(0, description="Total SOL invested")

    # Sidebet fields
    sidebetActive: bool | None = Field(None, description="Has active sidebet")
    sideBet: SideBet | None = Field(None, description="Active sidebet details")

    # Short position
    shortPosition: ShortPosition | None = Field(None, description="Short position details")

    # Cosmetic fields
    selectedCoin: str | None = Field(None, description="Selected coin ticker")
    position: int = Field(0, description="Leaderboard rank position")

    @field_validator(
        "pnl",
        "regularPnl",
        "sidebetPnl",
        "shortPnl",
        "pnlPercent",
        "positionQty",
        "avgCost",
        "totalInvested",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return Decimal(0)
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class PartialPrices(BaseModel):
    """
    Price history window for backfilling missed ticks.
    Used for continuity verification and latency analysis.
    """

    startTick: int = Field(..., description="Window start tick")
    endTick: int = Field(..., description="Window end tick")
    values: dict[str, Decimal] = Field(..., description="Tick-indexed price map")

    @field_validator("values", mode="before")
    @classmethod
    def coerce_values(cls, v):
        """Coerce float values to Decimal."""
        if isinstance(v, dict):
            return {k: Decimal(str(val)) if isinstance(val, float) else val for k, val in v.items()}
        return v


class GameHistoryEntry(BaseModel):
    """Summary of a completed game in game history array."""

    id: str = Field(..., description="Game ID")
    timestamp: int = Field(..., description="Game completion timestamp (ms)")
    prices: list[Decimal] = Field(..., description="Full price history")
    rugged: bool = Field(..., description="Game rugged")
    rugPoint: Decimal = Field(..., description="Final rug multiplier")

    @field_validator("prices", mode="before")
    @classmethod
    def coerce_prices(cls, v):
        if isinstance(v, list):
            return [Decimal(str(p)) if isinstance(p, float) else p for p in v]
        return v

    @field_validator("rugPoint", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class ProvablyFair(BaseModel):
    """Provably fair cryptographic proof data."""

    serverSeedHash: str = Field(..., description="Server seed hash (hex)")
    version: str = Field(..., description="Provably fair version")


class RugRoyaleMatch(BaseModel):
    """Current Rug Royale tournament match."""

    matchId: str
    round: int
    totalRounds: int
    leaderboard: list[dict[str, Any]] = Field(default_factory=list)
    savedAt: str | None = None


class RugRoyaleConfig(BaseModel):
    """Rug Royale tournament configuration."""

    token: str
    startingBalance: int
    prepTimeMinutes: int
    levelRequired: int
    prizeTiers: dict[str, Any] = Field(default_factory=dict)


class RugRoyale(BaseModel):
    """Rug Royale tournament state."""

    status: str = Field("INACTIVE", description="Tournament status")
    activeEventId: str | None = None
    currentEvent: RugRoyaleMatch | None = None
    upcomingEvents: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class AvailableShitcoin(BaseModel):
    """Available coin for betting."""

    address: str = Field(..., description="Coin contract address")
    ticker: str = Field(..., description="Coin ticker symbol")
    name: str = Field(..., description="Coin display name")
    max_bet: Decimal = Field(..., description="Maximum bet amount")
    max_win: Decimal = Field(..., description="Maximum win amount")

    @field_validator("max_bet", "max_win", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v


class RugpoolPlayerEntry(BaseModel):
    """Player entry in rugpool lottery."""

    playerId: str
    entries: int
    username: str | None = None
    percentage: Decimal

    @field_validator("percentage", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class RugpoolLastDrawing(BaseModel):
    """Last rugpool lottery drawing details."""

    timestamp: int
    winners: list[dict[str, Any]] = Field(default_factory=list)
    rewardPerWinner: Decimal
    totalPoolAmount: Decimal

    @field_validator("rewardPerWinner", "totalPoolAmount", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class RugpoolConfig(BaseModel):
    """Rugpool configuration."""

    threshold: int
    instarugThreshold: int
    rugpoolPercentage: Decimal

    @field_validator("rugpoolPercentage", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class Rugpool(BaseModel):
    """Rugpool lottery state (from gameStatePlayerUpdate)."""

    rugpoolAmount: Decimal = Field(..., description="Total SOL in lottery pool")
    threshold: int = Field(..., description="Instarug trigger threshold")
    instarugCount: int = Field(0, description="Instarug count this session")
    totalEntries: int | None = Field(None, description="Total lottery entries")
    playersWithEntries: int | None = Field(None, description="Players with entries")
    solPerEntry: Decimal | None = Field(None, description="Cost per entry (SOL)")
    maxEntriesPerPlayer: int | None = Field(None, description="Max entries per player")
    playerEntries: list[RugpoolPlayerEntry] = Field(default_factory=list)
    lastDrawing: RugpoolLastDrawing | None = None
    config: RugpoolConfig | None = None

    @field_validator("rugpoolAmount", "solPerEntry", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return v


# =============================================================================
# MAIN EVENT MODEL
# =============================================================================


class GameStatePlayerUpdate(BaseModel):
    """
    Player-specific rugpool state update.

    Broadcast alongside gameStateUpdate when the authenticated player
    has rugpool entries. Contains only gameId and rugpool lottery state.

    Socket.IO Format: 42["gameStatePlayerUpdate", {...}]
    Auth Required: YES - Only sent to authenticated players with entries

    Schema Version: 1.0.0
    GitHub Issue: #23 (Phase 0 Schema Validation)
    """

    gameId: str = Field(..., description="Unique game identifier")
    rugpool: Rugpool = Field(..., description="Rugpool lottery state for this player")

    class Config:
        """Pydantic model configuration."""

        extra = "allow"


class GameStateUpdate(BaseModel):
    """
    Primary tick event - the heartbeat of rugs.fun.

    Broadcast ~4x/second (~250ms intervals) to ALL connected clients.
    Contains complete game state including price, leaderboard, and history.

    This is the most critical event for game state synchronization.

    Socket.IO Format: 42["gameStateUpdate", {...}]
    Auth Required: NO
    """

    # ==========================================================================
    # CORE GAME STATE
    # Note: During cooldown (between games), active/rugged/price/tickCount may be omitted.
    # Defaults represent cooldown state (no active game).
    # ==========================================================================
    gameId: str = Field(..., description="Unique game identifier")
    gameVersion: str = Field("v3", description="Game version")
    active: bool = Field(False, description="Game in progress (False during cooldown)")
    rugged: bool = Field(False, description="Game has rugged (False during cooldown)")
    price: Decimal = Field(Decimal("1.0"), description="Current multiplier (1.0 during cooldown)")
    tickCount: int = Field(0, description="Current tick number (0 during cooldown)")

    # ==========================================================================
    # COOLDOWN/PAUSE STATE
    # ==========================================================================
    cooldownTimer: int = Field(0, description="Countdown to next game (0 = game active)")
    cooldownPaused: bool = Field(False, description="Countdown paused")
    pauseMessage: str = Field("", description="Pause reason message")
    allowPreRoundBuys: bool = Field(False, description="Pre-round buying enabled")

    # ==========================================================================
    # STATISTICS
    # ==========================================================================
    averageMultiplier: Decimal | None = Field(None, description="Session average rug point")
    connectedPlayers: int = Field(0, description="Current player count")
    count2x: int = Field(0, description="Games reaching 2x")
    count10x: int = Field(0, description="Games reaching 10x")
    count50x: int = Field(0, description="Games reaching 50x")
    count100x: int = Field(0, description="Games reaching 100x")
    highestToday: Decimal | None = Field(None, description="Daily high multiplier")
    highestTodayTimestamp: int | None = Field(None, description="Timestamp of daily high")
    highestTodayPrices: list[Decimal] | None = Field(
        None, description="Price history for daily high"
    )

    # ==========================================================================
    # GOD CANDLE CELEBRATIONS
    # ==========================================================================
    godCandle2x: Decimal | None = Field(None, description="2x celebration price")
    godCandle2xTimestamp: int | None = Field(None, description="When 2x was hit")
    godCandle2xPrices: list[Decimal] | None = Field(None, description="Price history for 2x candle")
    godCandle2xMassiveJump: bool | None = Field(None, description="Large price jump indicator")

    godCandle10x: Decimal | None = Field(None, description="10x celebration price")
    godCandle10xTimestamp: int | None = Field(None, description="When 10x was hit")
    godCandle10xPrices: list[Decimal] | None = Field(
        None, description="Price history for 10x candle"
    )
    godCandle10xMassiveJump: bool | None = Field(None, description="Large price jump indicator")

    godCandle50x: Decimal | None = Field(None, description="50x celebration price")
    godCandle50xTimestamp: int | None = Field(None, description="When 50x was hit")
    godCandle50xPrices: list[Decimal] | None = Field(
        None, description="Price history for 50x candle"
    )
    godCandle50xMassiveJump: bool | None = Field(None, description="Large price jump indicator")

    # ==========================================================================
    # NESTED STRUCTURES
    # ==========================================================================
    leaderboard: list[LeaderboardEntry] = Field(
        default_factory=list, description="Player leaderboard"
    )
    partialPrices: PartialPrices | None = Field(None, description="Price history window")
    gameHistory: list[GameHistoryEntry] = Field(
        default_factory=list, description="Recent game summaries"
    )
    provablyFair: ProvablyFair | None = Field(None, description="Cryptographic proof")
    rugRoyale: RugRoyale | None = Field(None, description="Tournament state")
    availableShitcoins: list[AvailableShitcoin] = Field(
        default_factory=list, description="Available coins"
    )
    rugpool: Rugpool | None = Field(None, description="Rugpool lottery state")

    # ==========================================================================
    # INGESTION METADATA (added by VECTRA-PLAYER, not from socket)
    # ==========================================================================
    meta_ts: datetime | None = Field(None, description="Ingestion timestamp (UTC)")
    meta_seq: int | None = Field(None, description="Sequence number within session")
    meta_source: Literal["cdp", "public_ws", "replay", "ui"] | None = Field(
        None, description="Event source"
    )
    meta_session_id: str | None = Field(None, description="Recording session UUID")

    @field_validator(
        "price",
        "averageMultiplier",
        "highestToday",
        "godCandle2x",
        "godCandle10x",
        "godCandle50x",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator(
        "highestTodayPrices",
        "godCandle2xPrices",
        "godCandle10xPrices",
        "godCandle50xPrices",
        mode="before",
    )
    @classmethod
    def coerce_price_list(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [Decimal(str(p)) if isinstance(p, float) else p for p in v]
        return v

    class Config:
        """Pydantic model configuration."""

        # Allow extra fields to be captured (forward compatibility)
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True

    def get_player_by_id(self, player_id: str) -> LeaderboardEntry | None:
        """Find a player in the leaderboard by their ID."""
        for entry in self.leaderboard:
            if entry.id == player_id:
                return entry
        return None

    def get_player_by_username(self, username: str) -> LeaderboardEntry | None:
        """Find a player in the leaderboard by username."""
        for entry in self.leaderboard:
            if entry.username == username:
                return entry
        return None

    @property
    def is_game_active(self) -> bool:
        """True if game is active and not rugged."""
        return self.active and not self.rugged

    @property
    def is_cooldown(self) -> bool:
        """True if in cooldown between games."""
        return self.cooldownTimer > 0 or (not self.active and not self.rugged)
