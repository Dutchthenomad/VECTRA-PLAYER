"""
Foundation Event Types - Typed dataclasses for all Foundation event types.

These classes provide type-safe wrappers for events received from Foundation Service.
"""

from dataclasses import dataclass, field


@dataclass
class GameTickEvent:
    """
    Normalized game.tick event (from gameStateUpdate).

    Contains current game state including price, phase, and leaderboard.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    active: bool = False
    rugged: bool = False
    price: float = 1.0
    tick_count: int = 0
    cooldown_timer: int = 0
    allow_pre_round_buys: bool = False
    trade_count: int = 0
    phase: str = "UNKNOWN"
    game_history: list | None = None
    leaderboard: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "GameTickEvent":
        """Create GameTickEvent from Foundation normalized dict."""
        inner_data = data.get("data", {}) or {}
        return cls(
            type=data.get("type", "game.tick"),
            ts=data.get("ts", 0),
            game_id=data.get("gameId"),
            seq=data.get("seq", 0),
            active=inner_data.get("active", False),
            rugged=inner_data.get("rugged", False),
            price=inner_data.get("price", 1.0),
            tick_count=inner_data.get("tickCount", 0),
            cooldown_timer=inner_data.get("cooldownTimer", 0),
            allow_pre_round_buys=inner_data.get("allowPreRoundBuys", False),
            trade_count=inner_data.get("tradeCount", 0),
            phase=inner_data.get("phase", "UNKNOWN"),
            game_history=inner_data.get("gameHistory"),
            leaderboard=inner_data.get("leaderboard", []) or [],
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "active": self.active,
            "rugged": self.rugged,
            "price": self.price,
            "tickCount": self.tick_count,
            "cooldownTimer": self.cooldown_timer,
            "allowPreRoundBuys": self.allow_pre_round_buys,
            "tradeCount": self.trade_count,
            "phase": self.phase,
            "gameHistory": self.game_history,
            "leaderboard": self.leaderboard,
        }


@dataclass
class PlayerStateEvent:
    """
    Normalized player.state event (from playerUpdate).

    Contains player balance and position information.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    cash: float = 0.0
    position_qty: float = 0.0
    avg_cost: float = 0.0
    cumulative_pnl: float = 0.0
    total_invested: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerStateEvent":
        """Create PlayerStateEvent from Foundation normalized dict."""
        inner_data = data.get("data", {}) or {}
        return cls(
            type=data.get("type", "player.state"),
            ts=data.get("ts", 0),
            game_id=data.get("gameId"),
            seq=data.get("seq", 0),
            cash=inner_data.get("cash", 0.0),
            position_qty=inner_data.get("positionQty", 0.0),
            avg_cost=inner_data.get("avgCost", 0.0),
            cumulative_pnl=inner_data.get("cumulativePnL", 0.0),
            total_invested=inner_data.get("totalInvested", 0.0),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "cash": self.cash,
            "positionQty": self.position_qty,
            "avgCost": self.avg_cost,
            "cumulativePnL": self.cumulative_pnl,
            "totalInvested": self.total_invested,
        }


@dataclass
class ConnectionAuthenticatedEvent:
    """
    Normalized connection.authenticated event (from usernameStatus).

    Contains player identity information.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    player_id: str | None = None
    username: str | None = None
    has_username: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionAuthenticatedEvent":
        """Create ConnectionAuthenticatedEvent from Foundation normalized dict."""
        inner_data = data.get("data", {}) or {}
        return cls(
            type=data.get("type", "connection.authenticated"),
            ts=data.get("ts", 0),
            game_id=data.get("gameId"),
            seq=data.get("seq", 0),
            player_id=inner_data.get("player_id") or inner_data.get("id"),
            username=inner_data.get("username"),
            has_username=inner_data.get("hasUsername", False),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "player_id": self.player_id,
            "username": self.username,
            "hasUsername": self.has_username,
        }


@dataclass
class PlayerTradeEvent:
    """
    Normalized player.trade event (from standard/newTrade).

    Contains trade information from other players.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    username: str | None = None
    trade_type: str | None = None  # "buy" or "sell"
    qty: float = 0.0
    price: float = 0.0
    player_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerTradeEvent":
        """Create PlayerTradeEvent from Foundation normalized dict."""
        inner_data = data.get("data", {}) or {}
        return cls(
            type=data.get("type", "player.trade"),
            ts=data.get("ts", 0),
            game_id=data.get("gameId"),
            seq=data.get("seq", 0),
            username=inner_data.get("username"),
            trade_type=inner_data.get("type"),
            qty=inner_data.get("qty", 0.0),
            price=inner_data.get("price", 0.0),
            player_id=inner_data.get("playerId"),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "username": self.username,
            "tradeType": self.trade_type,
            "qty": self.qty,
            "price": self.price,
            "playerId": self.player_id,
        }


@dataclass
class SidebetEvent:
    """
    Normalized sidebet.placed event (from currentSidebet).

    Contains sidebet placement information.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    amount: float = 0.0
    prediction: str | None = None  # "higher" or "lower"
    target_tick: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "SidebetEvent":
        """Create SidebetEvent from Foundation normalized dict."""
        inner_data = data.get("data", {}) or {}
        return cls(
            type=data.get("type", "sidebet.placed"),
            ts=data.get("ts", 0),
            game_id=data.get("gameId"),
            seq=data.get("seq", 0),
            amount=inner_data.get("amount", 0.0),
            prediction=inner_data.get("prediction"),
            target_tick=inner_data.get("targetTick", 0),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "amount": self.amount,
            "prediction": self.prediction,
            "targetTick": self.target_tick,
        }


@dataclass
class SidebetResultEvent:
    """
    Normalized sidebet.result event (from currentSidebetResult).

    Contains sidebet outcome information.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    won: bool = False
    payout: float = 0.0
    prediction: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "SidebetResultEvent":
        """Create SidebetResultEvent from Foundation normalized dict."""
        inner_data = data.get("data", {}) or {}
        return cls(
            type=data.get("type", "sidebet.result"),
            ts=data.get("ts", 0),
            game_id=data.get("gameId"),
            seq=data.get("seq", 0),
            won=inner_data.get("won", False),
            payout=inner_data.get("payout", 0.0),
            prediction=inner_data.get("prediction"),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "won": self.won,
            "payout": self.payout,
            "prediction": self.prediction,
        }


@dataclass
class RawEvent:
    """
    Container for unknown/raw event types.

    Preserves all data from events that don't match known types.
    Useful for rugs-expert discovery of new event types.
    """

    type: str
    ts: int
    game_id: str | None
    seq: int
    data: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw_data: dict) -> "RawEvent":
        """Create RawEvent from any dict."""
        return cls(
            type=raw_data.get("type", "raw.unknown"),
            ts=raw_data.get("ts", 0),
            game_id=raw_data.get("gameId"),
            seq=raw_data.get("seq", 0),
            data=raw_data.get("data", {}),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "data": self.data,
        }


# Event type mapping for factory
EVENT_TYPE_MAP = {
    "game.tick": GameTickEvent,
    "player.state": PlayerStateEvent,
    "connection.authenticated": ConnectionAuthenticatedEvent,
    "player.trade": PlayerTradeEvent,
    "sidebet.placed": SidebetEvent,
    "sidebet.result": SidebetResultEvent,
}


def parse_event(
    data: dict,
) -> (
    GameTickEvent
    | PlayerStateEvent
    | ConnectionAuthenticatedEvent
    | PlayerTradeEvent
    | SidebetEvent
    | SidebetResultEvent
    | RawEvent
):
    """
    Parse raw event dict into typed event class.

    Args:
        data: Raw event dict from Foundation Service

    Returns:
        Typed event instance based on event type
    """
    event_type = data.get("type", "")
    event_class = EVENT_TYPE_MAP.get(event_type)

    if event_class is not None:
        return event_class.from_dict(data)
    else:
        return RawEvent.from_dict(data)
