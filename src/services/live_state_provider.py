"""
LiveStateProvider - Server-Authoritative State in Live Mode

Phase 12C: Provides server-authoritative state from playerUpdate WebSocket events.

In live mode, this provider is the source of truth for:
- Balance (cash)
- Position quantity
- Average entry price (avg_cost)
- Cumulative P&L
- Total invested

The UI should query this provider when in live mode instead of
relying on locally calculated values from GameState.

Usage:
    live_provider = LiveStateProvider(event_bus)

    if live_provider.is_connected:
        balance = live_provider.cash
        position = live_provider.position_qty
"""

import logging
import threading
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from services.event_bus import EventBus, Events

logger = logging.getLogger(__name__)


@dataclass
class LiveState:
    """Server-authoritative player state from playerUpdate events."""

    cash: Decimal = field(default_factory=lambda: Decimal("0"))
    position_qty: Decimal = field(default_factory=lambda: Decimal("0"))
    avg_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    cumulative_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    total_invested: Decimal = field(default_factory=lambda: Decimal("0"))

    # Player identity
    player_id: str | None = None
    username: str | None = None
    game_id: str | None = None

    # Tick tracking (from gameStateUpdate)
    current_tick: int = 0
    current_multiplier: Decimal = field(default_factory=lambda: Decimal("1.0"))

    # Update tracking
    last_update_seq: int = 0


class LiveStateProvider:
    """
    Provides server-authoritative state in live mode.

    Subscribes to EventBus for:
    - PLAYER_UPDATE: Server state from playerUpdate WebSocket events
    - WS_SOURCE_CHANGED: Track live vs replay/fallback mode
    - GAME_TICK: Track current price/tick from server

    Thread-safe: All state access is protected by lock.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize LiveStateProvider.

        Args:
            event_bus: EventBus instance to subscribe to
        """
        self._event_bus = event_bus
        self._state = LiveState()
        self._connected = False
        self._source = "unknown"  # "cdp", "public_ws", "replay"
        self._lock = threading.RLock()

        # Subscribe to relevant events
        self._event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update, weak=False)
        self._event_bus.subscribe(Events.WS_SOURCE_CHANGED, self._on_source_changed, weak=False)
        self._event_bus.subscribe(Events.GAME_TICK, self._on_game_tick, weak=False)

        logger.info("LiveStateProvider initialized")

    # ========== Properties (Thread-safe getters) ==========

    @property
    def is_connected(self) -> bool:
        """True if receiving live data from CDP or public WebSocket."""
        with self._lock:
            return self._connected

    @property
    def is_live(self) -> bool:
        """True if in live mode (cdp or public_ws), not replay."""
        with self._lock:
            return self._source in ("cdp", "public_ws")

    @property
    def source(self) -> str:
        """Current data source: 'cdp', 'public_ws', 'replay', or 'unknown'."""
        with self._lock:
            return self._source

    @property
    def cash(self) -> Decimal:
        """Server-reported cash balance."""
        with self._lock:
            return self._state.cash

    @property
    def position_qty(self) -> Decimal:
        """Server-reported position quantity."""
        with self._lock:
            return self._state.position_qty

    @property
    def avg_cost(self) -> Decimal:
        """Server-reported average entry cost (avg_cost)."""
        with self._lock:
            return self._state.avg_cost

    @property
    def cumulative_pnl(self) -> Decimal:
        """Server-reported cumulative P&L."""
        with self._lock:
            return self._state.cumulative_pnl

    @property
    def total_invested(self) -> Decimal:
        """Server-reported total invested."""
        with self._lock:
            return self._state.total_invested

    @property
    def player_id(self) -> str | None:
        """Player DID (decentralized ID)."""
        with self._lock:
            return self._state.player_id

    @property
    def username(self) -> str | None:
        """Player display name."""
        with self._lock:
            return self._state.username

    @property
    def game_id(self) -> str | None:
        """Current game ID."""
        with self._lock:
            return self._state.game_id

    @property
    def current_tick(self) -> int:
        """Current game tick."""
        with self._lock:
            return self._state.current_tick

    @property
    def current_multiplier(self) -> Decimal:
        """Current price multiplier."""
        with self._lock:
            return self._state.current_multiplier

    # ========== Computed Properties ==========

    @property
    def has_position(self) -> bool:
        """True if player has an open position."""
        with self._lock:
            return self._state.position_qty > Decimal("0")

    @property
    def unrealized_pnl(self) -> Decimal:
        """
        Calculate unrealized P&L based on current position and price.

        P&L = (current_price - avg_cost) * position_qty
        """
        with self._lock:
            if self._state.position_qty <= Decimal("0"):
                return Decimal("0")

            if self._state.avg_cost <= Decimal("0"):
                return Decimal("0")

            # P&L = (current_multiplier - avg_cost) * position_qty
            return (
                self._state.current_multiplier - self._state.avg_cost
            ) * self._state.position_qty

    @property
    def position_value(self) -> Decimal:
        """Current value of open position at market price."""
        with self._lock:
            return self._state.position_qty * self._state.current_multiplier

    # ========== State Snapshot ==========

    def get_snapshot(self) -> dict[str, Any]:
        """
        Get a complete snapshot of live state.

        Returns:
            Dict with all current state values
        """
        with self._lock:
            return {
                "connected": self._connected,
                "source": self._source,
                "is_live": self._source in ("cdp", "public_ws"),
                "cash": self._state.cash,
                "position_qty": self._state.position_qty,
                "avg_cost": self._state.avg_cost,
                "cumulative_pnl": self._state.cumulative_pnl,
                "total_invested": self._state.total_invested,
                "player_id": self._state.player_id,
                "username": self._state.username,
                "game_id": self._state.game_id,
                "current_tick": self._state.current_tick,
                "current_multiplier": self._state.current_multiplier,
                "unrealized_pnl": self.unrealized_pnl,
                "position_value": self.position_value,
                "last_update_seq": self._state.last_update_seq,
            }

    # ========== Event Handlers ==========

    @staticmethod
    def _normalize_player_update(data: dict[str, Any]) -> dict[str, Any]:
        """Normalize playerUpdate payloads from multiple producers."""
        server_state = data.get("server_state")
        if server_state is not None:
            return {
                "cash": getattr(server_state, "cash", None),
                "positionQty": getattr(server_state, "position_qty", None),
                "avgCost": getattr(server_state, "avg_cost", None),
                "cumulativePnL": getattr(server_state, "cumulative_pnl", None),
                "totalInvested": getattr(server_state, "total_invested", None),
                "playerId": getattr(server_state, "player_id", None),
                "username": getattr(server_state, "username", None),
                "gameId": getattr(server_state, "game_id", None),
            }

        raw_data = data.get("raw_data")
        if isinstance(raw_data, dict):
            return raw_data

        return data

    def _on_player_update(self, wrapped: dict[str, Any]) -> None:
        """
        Handle PLAYER_UPDATE events from EventBus.

        These contain server-authoritative player state from playerUpdate
        WebSocket events captured by CDP or public WebSocket.
        """
        try:
            # EventBus wraps: {"name": event_type, "data": actual_data}
            data = wrapped.get("data", wrapped)
            if not isinstance(data, dict):
                return
            data = self._normalize_player_update(data)

            with self._lock:
                # Update cash/balance
                if data.get("cash") is not None:
                    self._state.cash = Decimal(str(data["cash"]))

                # Update position
                if data.get("positionQty") is not None:
                    self._state.position_qty = Decimal(str(data["positionQty"]))

                if data.get("avgCost") is not None:
                    self._state.avg_cost = Decimal(str(data["avgCost"]))

                # Update P&L tracking
                if data.get("cumulativePnL") is not None:
                    self._state.cumulative_pnl = Decimal(str(data["cumulativePnL"]))

                if data.get("totalInvested") is not None:
                    self._state.total_invested = Decimal(str(data["totalInvested"]))

                # Update identity
                if data.get("playerId") is not None:
                    self._state.player_id = data["playerId"]

                if data.get("username") is not None:
                    self._state.username = data["username"]

                if data.get("gameId") is not None:
                    self._state.game_id = data["gameId"]

                # Track update sequence
                self._state.last_update_seq += 1

                # Mark as connected if we got valid data
                if not self._connected:
                    self._connected = True
                    logger.info(
                        f"LiveStateProvider connected: player={self._state.username}, "
                        f"cash={self._state.cash}"
                    )

            logger.debug(
                f"PLAYER_UPDATE: cash={self._state.cash}, "
                f"position={self._state.position_qty}, "
                f"avg_cost={self._state.avg_cost}"
            )

        except Exception as e:
            logger.error(f"Error handling PLAYER_UPDATE: {e}")

    def _on_source_changed(self, wrapped: dict[str, Any]) -> None:
        """
        Handle WS_SOURCE_CHANGED events from EventBus.

        Tracks whether we're receiving from CDP, public WS, or replay.
        """
        try:
            data = wrapped.get("data", wrapped)
            if not isinstance(data, dict):
                return

            new_source = data.get("source", "unknown")

            with self._lock:
                old_source = self._source
                self._source = new_source

                # Reset connection state on source change
                if new_source != old_source:
                    logger.info(f"LiveStateProvider source changed: {old_source} -> {new_source}")

                    # If switching to replay, we're no longer "live"
                    if new_source == "replay":
                        self._connected = False

        except Exception as e:
            logger.error(f"Error handling WS_SOURCE_CHANGED: {e}")

    def _on_game_tick(self, wrapped: dict[str, Any]) -> None:
        """
        Handle GAME_TICK events from EventBus.

        Updates current tick and multiplier for P&L calculations.
        """
        try:
            data = wrapped.get("data", wrapped)
            if not isinstance(data, dict):
                return

            with self._lock:
                tick_value = data.get("tick")
                if tick_value is not None and hasattr(tick_value, "tick"):
                    self._state.current_tick = tick_value.tick
                    self._state.current_multiplier = Decimal(str(tick_value.price))
                    self._state.game_id = tick_value.game_id
                    return

                # Update tick
                if "tick" in data and isinstance(data["tick"], int):
                    self._state.current_tick = data["tick"]

                # Update multiplier/price
                if "multiplier" in data:
                    self._state.current_multiplier = Decimal(str(data["multiplier"]))
                elif "price" in data:
                    self._state.current_multiplier = Decimal(str(data["price"]))

                # Update game ID
                if "gameId" in data:
                    self._state.game_id = data["gameId"]

        except Exception as e:
            logger.error(f"Error handling GAME_TICK: {e}")

    # ========== Cleanup ==========

    def stop(self) -> None:
        """Unsubscribe from all events and cleanup."""
        try:
            self._event_bus.unsubscribe(Events.PLAYER_UPDATE, self._on_player_update)
            self._event_bus.unsubscribe(Events.WS_SOURCE_CHANGED, self._on_source_changed)
            self._event_bus.unsubscribe(Events.GAME_TICK, self._on_game_tick)
            logger.info("LiveStateProvider stopped")
        except Exception as e:
            logger.warning(f"Error during LiveStateProvider cleanup: {e}")

    def __enter__(self) -> "LiveStateProvider":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
