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
from typing import Optional, List, Dict, Any, Literal
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

    @field_validator('betSize', mode='before')
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

    @field_validator('amount', 'entryPrice', mode='before')
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
    username: Optional[str] = Field(None, description="Display name (null if not set)")
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
    sidebetActive: Optional[bool] = Field(None, description="Has active sidebet")
    sideBet: Optional[SideBet] = Field(None, description="Active sidebet details")

    # Short position
    shortPosition: Optional[ShortPosition] = Field(None, description="Short position details")

    # Cosmetic fields
    selectedCoin: Optional[str] = Field(None, description="Selected coin ticker")
    position: int = Field(0, description="Leaderboard rank position")

    @field_validator('pnl', 'regularPnl', 'sidebetPnl', 'shortPnl', 'pnlPercent',
                    'positionQty', 'avgCost', 'totalInvested', mode='before')
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
    values: Dict[str, Decimal] = Field(..., description="Tick-indexed price map")

    @field_validator('values', mode='before')
    @classmethod
    def coerce_values(cls, v):
        """Coerce float values to Decimal."""
        if isinstance(v, dict):
            return {k: Decimal(str(val)) if isinstance(val, float) else val
                    for k, val in v.items()}
        return v


class GameHistoryEntry(BaseModel):
    """Summary of a completed game in game history array."""
    id: str = Field(..., description="Game ID")
    timestamp: int = Field(..., description="Game completion timestamp (ms)")
    prices: List[Decimal] = Field(..., description="Full price history")
    rugged: bool = Field(..., description="Game rugged")
    rugPoint: Decimal = Field(..., description="Final rug multiplier")

    @field_validator('prices', mode='before')
    @classmethod
    def coerce_prices(cls, v):
        if isinstance(v, list):
            return [Decimal(str(p)) if isinstance(p, float) else p for p in v]
        return v

    @field_validator('rugPoint', mode='before')
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
    leaderboard: List[Dict[str, Any]] = Field(default_factory=list)
    savedAt: Optional[str] = None


class RugRoyaleConfig(BaseModel):
    """Rug Royale tournament configuration."""
    token: str
    startingBalance: int
    prepTimeMinutes: int
    levelRequired: int
    prizeTiers: Dict[str, Any] = Field(default_factory=dict)


class RugRoyale(BaseModel):
    """Rug Royale tournament state."""
    status: str = Field("INACTIVE", description="Tournament status")
    activeEventId: Optional[str] = None
    currentEvent: Optional[RugRoyaleMatch] = None
    upcomingEvents: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)


class AvailableShitcoin(BaseModel):
    """Available coin for betting."""
    address: str = Field(..., description="Coin contract address")
    ticker: str = Field(..., description="Coin ticker symbol")
    name: str = Field(..., description="Coin display name")
    max_bet: Decimal = Field(..., description="Maximum bet amount")
    max_win: Decimal = Field(..., description="Maximum win amount")

    @field_validator('max_bet', 'max_win', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v


class RugpoolPlayerEntry(BaseModel):
    """Player entry in rugpool lottery."""
    playerId: str
    entries: int
    username: Optional[str] = None
    percentage: Decimal

    @field_validator('percentage', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class RugpoolLastDrawing(BaseModel):
    """Last rugpool lottery drawing details."""
    timestamp: int
    winners: List[Dict[str, Any]] = Field(default_factory=list)
    rewardPerWinner: Decimal
    totalPoolAmount: Decimal

    @field_validator('rewardPerWinner', 'totalPoolAmount', mode='before')
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

    @field_validator('rugpoolPercentage', mode='before')
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
    totalEntries: Optional[int] = Field(None, description="Total lottery entries")
    playersWithEntries: Optional[int] = Field(None, description="Players with entries")
    solPerEntry: Optional[Decimal] = Field(None, description="Cost per entry (SOL)")
    maxEntriesPerPlayer: Optional[int] = Field(None, description="Max entries per player")
    playerEntries: List[RugpoolPlayerEntry] = Field(default_factory=list)
    lastDrawing: Optional[RugpoolLastDrawing] = None
    config: Optional[RugpoolConfig] = None

    @field_validator('rugpoolAmount', 'solPerEntry', mode='before')
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
    # ==========================================================================
    gameId: str = Field(..., description="Unique game identifier")
    gameVersion: str = Field("v3", description="Game version")
    active: bool = Field(..., description="Game in progress")
    rugged: bool = Field(..., description="Game has rugged")
    price: Decimal = Field(..., description="Current multiplier (server-authoritative)")
    tickCount: int = Field(..., description="Current tick number")

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
    averageMultiplier: Optional[Decimal] = Field(None, description="Session average rug point")
    connectedPlayers: int = Field(0, description="Current player count")
    count2x: int = Field(0, description="Games reaching 2x")
    count10x: int = Field(0, description="Games reaching 10x")
    count50x: int = Field(0, description="Games reaching 50x")
    count100x: int = Field(0, description="Games reaching 100x")
    highestToday: Optional[Decimal] = Field(None, description="Daily high multiplier")
    highestTodayTimestamp: Optional[int] = Field(None, description="Timestamp of daily high")
    highestTodayPrices: Optional[List[Decimal]] = Field(None, description="Price history for daily high")

    # ==========================================================================
    # GOD CANDLE CELEBRATIONS
    # ==========================================================================
    godCandle2x: Optional[Decimal] = Field(None, description="2x celebration price")
    godCandle2xTimestamp: Optional[int] = Field(None, description="When 2x was hit")
    godCandle2xPrices: Optional[List[Decimal]] = Field(None, description="Price history for 2x candle")
    godCandle2xMassiveJump: Optional[bool] = Field(None, description="Large price jump indicator")

    godCandle10x: Optional[Decimal] = Field(None, description="10x celebration price")
    godCandle10xTimestamp: Optional[int] = Field(None, description="When 10x was hit")
    godCandle10xPrices: Optional[List[Decimal]] = Field(None, description="Price history for 10x candle")
    godCandle10xMassiveJump: Optional[bool] = Field(None, description="Large price jump indicator")

    godCandle50x: Optional[Decimal] = Field(None, description="50x celebration price")
    godCandle50xTimestamp: Optional[int] = Field(None, description="When 50x was hit")
    godCandle50xPrices: Optional[List[Decimal]] = Field(None, description="Price history for 50x candle")
    godCandle50xMassiveJump: Optional[bool] = Field(None, description="Large price jump indicator")

    # ==========================================================================
    # NESTED STRUCTURES
    # ==========================================================================
    leaderboard: List[LeaderboardEntry] = Field(default_factory=list, description="Player leaderboard")
    partialPrices: Optional[PartialPrices] = Field(None, description="Price history window")
    gameHistory: List[GameHistoryEntry] = Field(default_factory=list, description="Recent game summaries")
    provablyFair: Optional[ProvablyFair] = Field(None, description="Cryptographic proof")
    rugRoyale: Optional[RugRoyale] = Field(None, description="Tournament state")
    availableShitcoins: List[AvailableShitcoin] = Field(default_factory=list, description="Available coins")
    rugpool: Optional[Rugpool] = Field(None, description="Rugpool lottery state")

    # ==========================================================================
    # INGESTION METADATA (added by VECTRA-PLAYER, not from socket)
    # ==========================================================================
    meta_ts: Optional[datetime] = Field(None, description="Ingestion timestamp (UTC)")
    meta_seq: Optional[int] = Field(None, description="Sequence number within session")
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None, description="Event source")
    meta_session_id: Optional[str] = Field(None, description="Recording session UUID")

    @field_validator('price', 'averageMultiplier', 'highestToday',
                    'godCandle2x', 'godCandle10x', 'godCandle50x', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator('highestTodayPrices', 'godCandle2xPrices',
                    'godCandle10xPrices', 'godCandle50xPrices', mode='before')
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
        extra = 'allow'
        # Use enum values for serialization
        use_enum_values = True

    def get_player_by_id(self, player_id: str) -> Optional[LeaderboardEntry]:
        """Find a player in the leaderboard by their ID."""
        for entry in self.leaderboard:
            if entry.id == player_id:
                return entry
        return None

    def get_player_by_username(self, username: str) -> Optional[LeaderboardEntry]:
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
