"""
Foundation BaseSubscriber - Abstract base class for all Python subscribers.

All Python services that consume Foundation events MUST inherit from this class.
Enforces correct interface and provides typed event parsing.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from foundation.client import FoundationClient
from foundation.events import (
    GameTickEvent,
    PlayerStateEvent,
    PlayerTradeEvent,
    SidebetEvent,
    SidebetResultEvent,
)


class BaseSubscriber(ABC):
    """
    Abstract base class ALL Python subscribers MUST inherit.

    Enforces correct interface and automatically registers event handlers.

    Required methods (must implement):
    - on_game_tick(event: GameTickEvent)
    - on_player_state(event: PlayerStateEvent)
    - on_connection_change(connected: bool)

    Optional methods (default no-op):
    - on_player_trade(event: PlayerTradeEvent)
    - on_sidebet_placed(event: SidebetEvent)
    - on_sidebet_result(event: SidebetResultEvent)
    - on_raw_event(event: dict)

    Usage:
        class MySubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                print(f"Price: {event.price}")

            def on_player_state(self, event):
                print(f"Cash: {event.cash}")

            def on_connection_change(self, connected):
                print(f"Connected: {connected}")

        client = FoundationClient()
        subscriber = MySubscriber(client)
        await client.connect()
    """

    def __init__(self, client: FoundationClient):
        """
        Initialize subscriber with Foundation client.

        Args:
            client: FoundationClient instance to subscribe to
        """
        self._client = client
        self._unsubscribe_functions: list[Callable[[], None]] = []
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register event handlers with client."""
        # Required handlers
        self._register("game.tick", self._handle_game_tick)
        self._register("player.state", self._handle_player_state)
        self._register("connection", self._handle_connection)

        # Optional handlers (only register if overridden)
        if self._is_overridden("on_player_trade"):
            self._register("player.trade", self._handle_player_trade)

        if self._is_overridden("on_sidebet_placed"):
            self._register("sidebet.placed", self._handle_sidebet_placed)

        if self._is_overridden("on_sidebet_result"):
            self._register("sidebet.result", self._handle_sidebet_result)

        # Always register wildcard for raw events if on_raw_event is overridden
        if self._is_overridden("on_raw_event"):
            self._register("*", self._handle_wildcard)

    def _is_overridden(self, method_name: str) -> bool:
        """Check if a method is overridden from BaseSubscriber."""
        base_method = getattr(BaseSubscriber, method_name, None)
        instance_method = getattr(self, method_name, None)
        if base_method is None or instance_method is None:
            return False
        return instance_method.__func__ is not base_method

    def _register(self, event_type: str, handler: Callable) -> None:
        """Register handler and store unsubscribe function."""
        unsub = self._client.on(event_type, handler)
        self._unsubscribe_functions.append(unsub)

    def _handle_game_tick(self, raw_event: dict) -> None:
        """Parse and forward game.tick event."""
        event = GameTickEvent.from_dict(raw_event)
        self.on_game_tick(event)

    def _handle_player_state(self, raw_event: dict) -> None:
        """Parse and forward player.state event."""
        event = PlayerStateEvent.from_dict(raw_event)
        self.on_player_state(event)

    def _handle_connection(self, raw_event: dict) -> None:
        """Forward connection state change."""
        connected = raw_event.get("connected", False)
        self.on_connection_change(connected)

    def _handle_player_trade(self, raw_event: dict) -> None:
        """Parse and forward player.trade event."""
        event = PlayerTradeEvent.from_dict(raw_event)
        self.on_player_trade(event)

    def _handle_sidebet_placed(self, raw_event: dict) -> None:
        """Parse and forward sidebet.placed event."""
        event = SidebetEvent.from_dict(raw_event)
        self.on_sidebet_placed(event)

    def _handle_sidebet_result(self, raw_event: dict) -> None:
        """Parse and forward sidebet.result event."""
        event = SidebetResultEvent.from_dict(raw_event)
        self.on_sidebet_result(event)

    def _handle_wildcard(self, raw_event: dict) -> None:
        """Forward raw/unknown events."""
        event_type = raw_event.get("type", "")
        # Only forward events that aren't handled by specific handlers
        if event_type.startswith("raw.") or event_type not in (
            "game.tick",
            "player.state",
            "connection",
            "player.trade",
            "sidebet.placed",
            "sidebet.result",
        ):
            self.on_raw_event(raw_event)

    def unsubscribe(self) -> None:
        """Remove all registered handlers."""
        for unsub in self._unsubscribe_functions:
            unsub()
        self._unsubscribe_functions.clear()

    # =========================================================================
    # REQUIRED METHODS (must implement)
    # =========================================================================

    @abstractmethod
    def on_game_tick(self, event: GameTickEvent) -> None:
        """
        Handle game.tick event.

        Called on every price/tick update.

        Args:
            event: Typed GameTickEvent with price, phase, leaderboard, etc.
        """
        ...

    @abstractmethod
    def on_player_state(self, event: PlayerStateEvent) -> None:
        """
        Handle player.state event.

        Called when player balance/position changes.

        Args:
            event: Typed PlayerStateEvent with cash, position, PnL, etc.
        """
        ...

    @abstractmethod
    def on_connection_change(self, connected: bool) -> None:
        """
        Handle connection state change.

        Called when WebSocket connects or disconnects.

        Args:
            connected: True if connected, False if disconnected
        """
        ...

    # =========================================================================
    # OPTIONAL METHODS (default no-op)
    # =========================================================================

    def on_player_trade(self, event: PlayerTradeEvent) -> None:  # noqa: B027
        """
        Handle player.trade event (optional).

        Called when another player makes a trade.

        Args:
            event: Typed PlayerTradeEvent with username, type, qty, price
        """

    def on_sidebet_placed(self, event: SidebetEvent) -> None:  # noqa: B027
        """
        Handle sidebet.placed event (optional).

        Called when a sidebet is placed.

        Args:
            event: Typed SidebetEvent with amount, prediction, target_tick
        """

    def on_sidebet_result(self, event: SidebetResultEvent) -> None:  # noqa: B027
        """
        Handle sidebet.result event (optional).

        Called when a sidebet resolves.

        Args:
            event: Typed SidebetResultEvent with won, payout, prediction
        """

    def on_raw_event(self, event: dict) -> None:  # noqa: B027
        """
        Handle unknown/raw events (optional).

        Called for events that don't match known types.
        Useful for rugs-expert discovery of new event types.

        Args:
            event: Raw event dict
        """
