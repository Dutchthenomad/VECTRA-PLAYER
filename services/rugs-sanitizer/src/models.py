"""
Pydantic models for sanitized rugs.fun WebSocket data.

All types derived from Rosetta Stone v0.2.0 field definitions.
Every field has explicit type, default, and validation rules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Phase(StrEnum):
    """Game phase derived from gameStateUpdate fields.

    Detection priority (Rosetta Stone Section 1.2):
    1. active=True and rugged=False -> ACTIVE
    2. rugged=True -> RUGGED
    3. cooldownTimer > 0 + allowPreRoundBuys -> PRESALE
    4. cooldownTimer > 0 -> COOLDOWN
    5. allowPreRoundBuys=True -> PRESALE (near-zero timer edge)
    6. Otherwise -> UNKNOWN
    """

    ACTIVE = "ACTIVE"
    RUGGED = "RUGGED"
    PRESALE = "PRESALE"
    COOLDOWN = "COOLDOWN"
    UNKNOWN = "UNKNOWN"


class TradeType(StrEnum):
    """Trade action type from standard/newTrade."""

    BUY = "buy"
    SELL = "sell"
    SHORT_OPEN = "short_open"
    SHORT_CLOSE = "short_close"


class Channel(StrEnum):
    """Output broadcast channels."""

    GAME = "game"
    STATS = "stats"
    TRADES = "trades"
    HISTORY = "history"
    ALL = "all"


# ---------------------------------------------------------------------------
# Sub-models (nested objects)
# ---------------------------------------------------------------------------


class PartialPrices(BaseModel):
    """Current candlestick data (5 ticks = 1.25s candle).

    Rosetta Stone Section 1.4.
    """

    start_tick: int = Field(description="First tick number in current candle")
    end_tick: int = Field(description="Last tick number in current candle (= tickCount)")
    values: dict[str, float] = Field(
        default_factory=dict,
        description="Map of tick number (string key) to price (float value)",
    )

    @classmethod
    def from_raw(cls, raw: dict | None) -> PartialPrices | None:
        if raw is None:
            return None
        return cls(
            start_tick=raw.get("startTick", 0),
            end_tick=raw.get("endTick", 0),
            values=raw.get("values", {}),
        )


class ProvablyFair(BaseModel):
    """Provably fair triplet data.

    Rosetta Stone Section 1.6.
    serverSeed only present after rug (first rug-transition broadcast).
    """

    server_seed_hash: str = Field(description="SHA-256 hash of server seed (64-char hex)")
    version: str = Field(default="v3", description="PRNG algorithm version")
    server_seed: str | None = Field(
        default=None,
        description="Revealed server seed (only post-rug)",
    )

    @classmethod
    def from_raw(cls, raw: dict | None) -> ProvablyFair | None:
        if raw is None:
            return None
        return cls(
            server_seed_hash=raw.get("serverSeedHash", ""),
            version=raw.get("version", "v3"),
            server_seed=raw.get("serverSeed"),
        )


class Rugpool(BaseModel):
    """Rugpool consolation prize state.

    Rosetta Stone Section 1.7.
    Strategic value: LOW.
    """

    instarug_count: int = Field(default=0, description="Insta-rugs toward next drawing")
    threshold: int = Field(default=10, description="Insta-rugs required for drawing")
    rugpool_amount: float = Field(default=0.0, description="SOL accumulated in pool")

    @classmethod
    def from_raw(cls, raw: dict | None) -> Rugpool | None:
        if raw is None:
            return None
        return cls(
            instarug_count=raw.get("instarugCount", 0),
            threshold=raw.get("threshold", 10),
            rugpool_amount=raw.get("rugpoolAmount", 0.0),
        )


class SideBet(BaseModel):
    """Active sidebet details.

    Rosetta Stone Section 1.9 (sideBet sub-object).
    40-tick hardcoded window, 5x fixed payout.
    """

    started_at_tick: int = Field(description="Tick when sidebet was placed")
    game_id: str = Field(description="Game ID")
    end: int = Field(description="Target tick (startedAtTick + 40, hardcoded)")
    bet_amount: float = Field(description="SOL wagered")
    x_payout: int = Field(default=5, description="Payout multiplier (always 5)")
    coin_address: str = Field(default="", description="Token contract address")
    bonus_portion: float = Field(default=0.0, description="Practice/bonus balance portion")
    real_portion: float = Field(default=0.0, description="Real SOL portion")

    @classmethod
    def from_raw(cls, raw: dict | None) -> SideBet | None:
        if raw is None:
            return None
        return cls(
            started_at_tick=raw.get("startedAtTick", 0),
            game_id=raw.get("gameId", ""),
            end=raw.get("end", 0),
            bet_amount=raw.get("betAmount", 0.0),
            x_payout=raw.get("xPayout", 5),
            coin_address=raw.get("coinAddress", ""),
            bonus_portion=raw.get("bonusPortion", 0.0),
            real_portion=raw.get("realPortion", 0.0),
        )


class ShortPosition(BaseModel):
    """Active short position details.

    Rosetta Stone Section 1.9 (shortPosition sub-object).
    PnL formula: TENTATIVE.
    """

    amount: float = Field(description="SOL committed to short")
    entry_price: float = Field(description="Price (multiplier) at open")
    entry_tick: int = Field(description="Tick when opened")
    current_value: float = Field(default=0.0, description="Current SOL value")
    pnl: float = Field(default=0.0, description="Unrealized PnL (TENTATIVE formula)")
    coin_address: str = Field(default="", description="Token contract address")
    bonus_portion: float = Field(default=0.0)
    real_portion: float = Field(default=0.0)

    @classmethod
    def from_raw(cls, raw: dict | None) -> ShortPosition | None:
        if raw is None:
            return None
        return cls(
            amount=raw.get("amount", 0.0),
            entry_price=raw.get("entryPrice", 0.0),
            entry_tick=raw.get("entryTick", 0),
            current_value=raw.get("currentValue", 0.0),
            pnl=raw.get("pnl", 0.0),
            coin_address=raw.get("coinAddress", ""),
            bonus_portion=raw.get("bonusPortion", 0.0),
            real_portion=raw.get("realPortion", 0.0),
        )


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry (top 10 by PnL).

    Rosetta Stone Section 1.9.
    Fields marked TENTATIVE: avgCost, totalInvested, short PnL formula.
    """

    id: str = Field(description="Player Privy DID")
    username: str = Field(default="")
    level: int = Field(default=0)
    pnl: float = Field(default=0.0, description="Total PnL (SOL)")
    regular_pnl: float = Field(default=0.0, description="Long position PnL")
    sidebet_pnl: float = Field(default=0.0, description="Sidebet PnL")
    short_pnl: float = Field(default=0.0, description="Short position PnL")
    pnl_percent: float = Field(default=0.0, description="PnL as percentage")
    has_active_trades: bool = Field(default=False)
    position_qty: float = Field(default=0.0, description="Token units held")
    avg_cost: float = Field(
        default=0.0,
        description="VWAP entry price (TENTATIVE)",
    )
    total_invested: float = Field(
        default=0.0,
        description="Cumulative SOL deployed (TENTATIVE)",
    )
    position: int = Field(default=0, description="Leaderboard rank (1=top)")
    selected_coin: dict[str, Any] | None = Field(
        default=None,
        description="Coin object or null for SOL",
    )
    sidebet_active: bool | None = Field(default=None)
    side_bet: SideBet | None = Field(default=None)
    short_position: ShortPosition | None = Field(default=None)

    @property
    def is_practice(self) -> bool:
        """Whether this player is using practice tokens."""
        if self.selected_coin is None:
            return False
        return self.selected_coin.get("address") == "0xPractice"

    @classmethod
    def from_raw(cls, raw: dict) -> LeaderboardEntry:
        # Wire sends null for many fields — coalesce to defaults
        return cls(
            id=raw.get("id") or "",
            username=raw.get("username") or "",
            level=raw.get("level") or 0,
            pnl=raw.get("pnl") or 0.0,
            regular_pnl=raw.get("regularPnl") or 0.0,
            sidebet_pnl=raw.get("sidebetPnl") or 0.0,
            short_pnl=raw.get("shortPnl") or 0.0,
            pnl_percent=raw.get("pnlPercent") or 0.0,
            has_active_trades=raw.get("hasActiveTrades") or False,
            position_qty=raw.get("positionQty") or 0.0,
            avg_cost=raw.get("avgCost") or 0.0,
            total_invested=raw.get("totalInvested") or 0.0,
            position=raw.get("position") or 0,
            selected_coin=raw.get("selectedCoin"),
            sidebet_active=raw.get("sidebetActive"),
            side_bet=SideBet.from_raw(raw.get("sideBet")),
            short_position=ShortPosition.from_raw(raw.get("shortPosition")),
        )


# ---------------------------------------------------------------------------
# God Candle tier (Section 1.11)
# ---------------------------------------------------------------------------


class GodCandleTier(BaseModel):
    """A single god candle tier record (2x, 10x, or 50x).

    HIGH PRIORITY CAPTURE FLAG when non-null.
    """

    multiplier: float | None = Field(default=None, description="Peak multiplier of gc game")
    timestamp: int | None = Field(default=None, description="Unix ms when gc occurred")
    game_id: str | None = Field(default=None)
    server_seed: str | None = Field(default=None)
    massive_jump: list[float] | None = Field(
        default=None,
        description="[jump_multiplier, resulting_price]",
    )


class DailyRecords(BaseModel):
    """Daily records and god candle tracking.

    Rosetta Stone Section 1.11.
    """

    highest_today: float | None = Field(default=None)
    highest_today_timestamp: int | None = Field(default=None)
    highest_today_game_id: str | None = Field(default=None)
    highest_today_server_seed: str | None = Field(default=None)
    god_candle_2x: GodCandleTier = Field(default_factory=GodCandleTier)
    god_candle_10x: GodCandleTier = Field(default_factory=GodCandleTier)
    god_candle_50x: GodCandleTier = Field(default_factory=GodCandleTier)

    @property
    def has_god_candle(self) -> bool:
        """True if any god candle tier is populated.

        NOTE: This is a stateless check on the wire data. The platform re-reports
        stale god candle data on every transition tick for the rest of the UTC day.
        Use GodCandleDetector for change-detection (new vs already-seen).
        """
        return any(
            tier.multiplier is not None
            for tier in (self.god_candle_2x, self.god_candle_10x, self.god_candle_50x)
        )

    @property
    def god_candle_game_ids(self) -> set[str]:
        """Return the set of non-null god candle game IDs across all tiers."""
        ids: set[str] = set()
        for tier in (self.god_candle_2x, self.god_candle_10x, self.god_candle_50x):
            if tier.game_id is not None:
                ids.add(tier.game_id)
        return ids

    @classmethod
    def from_raw(cls, data: dict) -> DailyRecords:
        def _tier(prefix: str) -> GodCandleTier:
            return GodCandleTier(
                multiplier=data.get(prefix),
                timestamp=data.get(f"{prefix}Timestamp"),
                game_id=data.get(f"{prefix}GameId"),
                server_seed=data.get(f"{prefix}ServerSeed"),
                massive_jump=data.get(f"{prefix}MassiveJump"),
            )

        return cls(
            highest_today=data.get("highestToday"),
            highest_today_timestamp=data.get("highestTodayTimestamp"),
            highest_today_game_id=data.get("highestTodayGameId"),
            highest_today_server_seed=data.get("highestTodayServerSeed"),
            god_candle_2x=_tier("godCandle2x"),
            god_candle_10x=_tier("godCandle10x"),
            god_candle_50x=_tier("godCandle50x"),
        )


# ---------------------------------------------------------------------------
# Top-level sanitized event models
# ---------------------------------------------------------------------------


class GameTick(BaseModel):
    """Core game state from gameStateUpdate.

    Rosetta Stone Sections 1.1-1.4.
    Broadcast on /feed/game channel.
    """

    game_id: str
    phase: Phase
    active: bool = False
    price: float = 1.0
    rugged: bool = False
    tick_count: int = 0
    trade_count: int | None = None
    cooldown_timer: int = 0
    cooldown_paused: bool = False
    allow_pre_round_buys: bool = False
    partial_prices: PartialPrices | None = None
    provably_fair: ProvablyFair | None = None
    rugpool: Rugpool | None = None
    leaderboard: list[LeaderboardEntry] = Field(default_factory=list)
    game_version: str | None = None

    # Transition-tick-only fields (rare ~0.5%)
    daily_records: DailyRecords | None = None
    has_god_candle: bool = Field(
        default=False,
        description="HIGH PRIORITY flag: true when any god candle tier is non-null",
    )

    @classmethod
    def from_raw(cls, data: dict, phase: Phase) -> GameTick:
        daily = None
        has_gc = False
        if data.get("highestToday") is not None:
            daily = DailyRecords.from_raw(data)
            has_gc = daily.has_god_candle

        return cls(
            game_id=data.get("gameId", ""),
            phase=phase,
            active=data.get("active", False),
            price=data.get("price", 1.0),
            rugged=data.get("rugged", False),
            tick_count=data.get("tickCount", 0),
            trade_count=data.get("tradeCount"),
            cooldown_timer=data.get("cooldownTimer", 0),
            cooldown_paused=data.get("cooldownPaused", False),
            allow_pre_round_buys=data.get("allowPreRoundBuys", False),
            partial_prices=PartialPrices.from_raw(data.get("partialPrices")),
            provably_fair=ProvablyFair.from_raw(data.get("provablyFair")),
            rugpool=Rugpool.from_raw(data.get("rugpool")),
            leaderboard=[LeaderboardEntry.from_raw(e) for e in data.get("leaderboard", [])],
            game_version=data.get("gameVersion"),
            daily_records=daily,
            has_god_candle=has_gc,
        )


class SessionStats(BaseModel):
    """Server-computed aggregate statistics.

    Rosetta Stone Section 1.5.
    Broadcast on /feed/stats channel.
    Updates only at game boundaries (except connectedPlayers).
    """

    connected_players: int = 0
    average_multiplier: float | None = None
    count_2x: int | None = None
    count_10x: int | None = None
    count_50x: int | None = None
    count_100x: int | None = None

    @classmethod
    def from_raw(cls, data: dict) -> SessionStats:
        return cls(
            connected_players=data.get("connectedPlayers", 0),
            average_multiplier=data.get("averageMultiplier"),
            count_2x=data.get("count2x"),
            count_10x=data.get("count10x"),
            count_50x=data.get("count50x"),
            count_100x=data.get("count100x"),
        )


class Trade(BaseModel):
    """Annotated trade from standard/newTrade.

    Rosetta Stone Event 2.
    Broadcast on /feed/trades channel.
    """

    # Core fields (always present)
    id: str
    game_id: str
    player_id: str
    username: str = ""
    level: int = 0
    price: float = 0.0
    type: TradeType
    tick_index: int = 0
    coin: str = "solana"
    amount: float = 0.0

    # Conditional fields
    qty: float = 0.0
    leverage: int | None = None
    bonus_portion: float | None = None
    real_portion: float | None = None

    # Inferred annotations (added by trade annotator)
    is_forced_sell: bool = Field(
        default=False,
        description="Inferred: sell during RUGGED phase",
    )
    is_liquidation: bool = Field(
        default=False,
        description="Inferred: leveraged position hit liquidation threshold",
    )
    is_practice: bool = Field(
        default=False,
        description="Inferred: trade uses practice token",
    )
    token_type: str = Field(
        default="unknown",
        description="'practice' | 'real' | 'unknown'",
    )

    @classmethod
    def from_raw(cls, data: dict) -> Trade:
        return cls(
            id=data.get("id") or "",
            game_id=data.get("gameId") or "",
            player_id=data.get("playerId") or "",
            username=data.get("username") or "",
            level=data.get("level") or 0,
            price=data.get("price") or 0.0,
            type=TradeType(data.get("type") or "buy"),
            tick_index=data.get("tickIndex") or 0,
            coin=data.get("coin") or "solana",
            amount=data.get("amount") or 0.0,
            qty=data.get("qty") or 0.0,
            leverage=data.get("leverage"),
            bonus_portion=data.get("bonusPortion"),
            real_portion=data.get("realPortion"),
        )


# ---------------------------------------------------------------------------
# Game History models (Section 1.10)
# ---------------------------------------------------------------------------


class GameHistoryProvablyFair(BaseModel):
    """Revealed provably fair data from completed game."""

    server_seed: str = ""
    server_seed_hash: str = ""


class GlobalSidebetEntry(BaseModel):
    """A sidebet record from gameHistory.globalSidebets."""

    id: str = ""
    player_id: str = ""
    username: str = ""
    game_id: str = ""
    type: str = ""  # "placed" or "payout"
    bet_amount: float = 0.0
    x_payout: int = 5
    coin_address: str = ""
    bonus_portion: float = 0.0
    real_portion: float = 0.0
    timestamp: int = 0
    # placed-specific
    started_at_tick: int | None = None
    end: int | None = None
    # payout-specific
    payout: float | None = None
    profit: float | None = None
    end_tick: int | None = None
    start_tick: int | None = None
    tick_index: int | None = None

    @classmethod
    def from_raw(cls, raw: dict) -> GlobalSidebetEntry:
        return cls(
            id=raw.get("id") or "",
            player_id=raw.get("playerId") or "",
            username=raw.get("username") or "",
            game_id=raw.get("gameId") or "",
            type=raw.get("type") or "",
            bet_amount=raw.get("betAmount") or 0.0,
            x_payout=raw.get("xPayout") or 5,
            coin_address=raw.get("coinAddress") or "",
            bonus_portion=raw.get("bonusPortion") or 0.0,
            real_portion=raw.get("realPortion") or 0.0,
            timestamp=raw.get("timestamp") or 0,
            started_at_tick=raw.get("startedAtTick"),
            end=raw.get("end"),
            payout=raw.get("payout"),
            profit=raw.get("profit"),
            end_tick=raw.get("endTick"),
            start_tick=raw.get("startTick"),
            tick_index=raw.get("tickIndex"),
        )


class GameHistoryRecord(BaseModel):
    """Complete game record from gameHistory rolling window.

    Rosetta Stone Section 1.10.
    Broadcast on /feed/history channel.
    """

    id: str = Field(description="Game ID")
    timestamp: int = Field(description="Unix ms when game ended")
    peak_multiplier: float = Field(default=0.0)
    rugged: bool = Field(default=True)
    game_version: str = Field(default="v3")
    prices: list[float] = Field(
        default_factory=list,
        description="Complete tick-by-tick price array",
    )
    global_trades: list[dict[str, Any]] = Field(
        default_factory=list,
        description="ALWAYS empty on public feed",
    )
    global_sidebets: list[GlobalSidebetEntry] = Field(default_factory=list)
    provably_fair: GameHistoryProvablyFair = Field(
        default_factory=GameHistoryProvablyFair,
    )

    @classmethod
    def from_raw(cls, raw: dict) -> GameHistoryRecord:
        pf = raw.get("provablyFair", {})
        return cls(
            id=raw.get("id", ""),
            timestamp=raw.get("timestamp", 0),
            peak_multiplier=raw.get("peakMultiplier", 0.0),
            rugged=raw.get("rugged", True),
            game_version=raw.get("gameVersion", "v3"),
            prices=raw.get("prices", []),
            global_trades=raw.get("globalTrades") or [],
            global_sidebets=[
                GlobalSidebetEntry.from_raw(s) for s in (raw.get("globalSidebets") or [])
            ],
            provably_fair=GameHistoryProvablyFair(
                server_seed=pf.get("serverSeed", ""),
                server_seed_hash=pf.get("serverSeedHash", ""),
            ),
        )


# ---------------------------------------------------------------------------
# Sanitized event envelope
# ---------------------------------------------------------------------------


class SanitizedEvent(BaseModel):
    """Output envelope wrapping all sanitized data.

    This is the wire format sent to downstream subscribers.
    """

    channel: Channel
    event_type: str = Field(description="Original rugs.fun event type")
    data: dict[str, Any] = Field(description="Sanitized model as dict")
    timestamp: str = Field(description="ISO 8601 timestamp")
    game_id: str = ""
    phase: Phase = Phase.UNKNOWN

    @classmethod
    def create(
        cls,
        channel: Channel,
        event_type: str,
        model: BaseModel,
        game_id: str = "",
        phase: Phase = Phase.UNKNOWN,
        timestamp: datetime | None = None,
    ) -> SanitizedEvent:
        ts = timestamp or datetime.now(UTC)
        return cls(
            channel=channel,
            event_type=event_type,
            data=model.model_dump(mode="json"),
            timestamp=ts.isoformat(),
            game_id=game_id,
            phase=phase,
        )
