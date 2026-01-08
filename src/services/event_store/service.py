"""
Event Store Service - EventBus integration for Parquet persistence

Phase 12B, Issue #25

Subscribes to EventBus events and persists them to Parquet storage.
"""

import logging
import threading
import uuid
from decimal import Decimal
from typing import Any

from services.event_bus import EventBus, Events
from services.event_store.paths import EventStorePaths
from services.event_store.schema import EventEnvelope, EventSource
from services.event_store.writer import ParquetWriter

logger = logging.getLogger(__name__)


class EventStoreService:
    """
    EventBus integration for Parquet event storage.

    Subscribes to relevant events and persists them to Parquet files.
    Single writer pattern - all persistence goes through this service.

    Usage:
        event_bus = EventBus()
        service = EventStoreService(event_bus)
        service.start()
        # ... application runs ...
        service.stop()
    """

    def __init__(
        self,
        event_bus: EventBus,
        paths: EventStorePaths | None = None,
        session_id: str | None = None,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
    ):
        """
        Initialize EventStoreService.

        Args:
            event_bus: EventBus instance to subscribe to
            paths: EventStorePaths instance (uses defaults if None)
            session_id: Recording session UUID (generates new if None)
            buffer_size: Events to buffer before write
            flush_interval: Seconds between time-based flushes
        """
        self._event_bus = event_bus
        self._paths = paths or EventStorePaths()
        self._session_id = session_id or str(uuid.uuid4())
        self._seq = 0
        self._seq_lock = threading.Lock()  # Thread-safe sequence numbers

        self._writer = ParquetWriter(
            paths=self._paths,
            buffer_size=buffer_size,
            flush_interval=flush_interval,
        )

        self._started = False
        self._paused = True  # Start paused by default (no recording until toggled)
        self._recorded_game_ids: set[str] = set()  # Track unique game_ids for deduplication
        self._total_events_recorded = 0  # Count of events persisted

        logger.info(f"EventStoreService initialized: session_id={self._session_id}")

    @property
    def session_id(self) -> str:
        """Current session ID"""
        return self._session_id

    @property
    def event_count(self) -> int:
        """Number of events in current buffer"""
        return self._writer.buffer_count

    @property
    def is_paused(self) -> bool:
        """Whether recording is currently paused."""
        return self._paused

    @property
    def is_recording(self) -> bool:
        """Whether actively recording events (started and not paused)."""
        return self._started and not self._paused

    @property
    def total_events_recorded(self) -> int:
        """Total number of events persisted across this session."""
        return self._total_events_recorded

    @property
    def recorded_game_ids(self) -> set[str]:
        """Set of unique game_ids that have been recorded (copy for safety)."""
        return self._recorded_game_ids.copy()

    def pause(self) -> None:
        """Pause event recording. Events will be dropped until resume() is called."""
        self._paused = True
        logger.info("Recording PAUSED")

    def resume(self) -> None:
        """Resume event recording."""
        self._paused = False
        logger.info("Recording RESUMED")

    def toggle_recording(self) -> bool:
        """
        Toggle recording state between paused and recording.

        Returns:
            bool: New recording state (True if now recording, False if paused)
        """
        if self._paused:
            self.resume()
        else:
            self.pause()
        return self.is_recording

    def start(self) -> None:
        """Start service and subscribe to events"""
        if self._started:
            logger.warning("EventStoreService already started")
            return

        # Subscribe to WebSocket events
        self._event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event, weak=False)
        logger.info(
            f"EventStoreService subscribed to WS_RAW_EVENT (event_bus id: {id(self._event_bus)})"
        )

        # Subscribe to game events
        self._event_bus.subscribe(Events.GAME_TICK, self._on_game_tick, weak=False)

        # Subscribe to player events
        self._event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update, weak=False)

        # Subscribe to trade events
        self._event_bus.subscribe(Events.TRADE_BUY, self._on_trade_buy, weak=False)
        self._event_bus.subscribe(Events.TRADE_SELL, self._on_trade_sell, weak=False)
        self._event_bus.subscribe(Events.TRADE_SIDEBET, self._on_trade_sidebet, weak=False)
        self._event_bus.subscribe(Events.TRADE_CONFIRMED, self._on_trade_confirmed, weak=False)

        # Subscribe to button events (Phase B: RL training data)
        self._event_bus.subscribe(Events.BUTTON_PRESS, self._on_button_press, weak=False)
        logger.info("EventStoreService subscribed to BUTTON_PRESS for RL training")

        self._started = True
        logger.info("EventStoreService started")

    def stop(self) -> None:
        """Stop service and flush remaining events"""
        if not self._started:
            return

        # Unsubscribe from all events
        self._event_bus.unsubscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event)
        self._event_bus.unsubscribe(Events.GAME_TICK, self._on_game_tick)
        self._event_bus.unsubscribe(Events.PLAYER_UPDATE, self._on_player_update)
        self._event_bus.unsubscribe(Events.TRADE_BUY, self._on_trade_buy)
        self._event_bus.unsubscribe(Events.TRADE_SELL, self._on_trade_sell)
        self._event_bus.unsubscribe(Events.TRADE_SIDEBET, self._on_trade_sidebet)
        self._event_bus.unsubscribe(Events.TRADE_CONFIRMED, self._on_trade_confirmed)
        self._event_bus.unsubscribe(Events.BUTTON_PRESS, self._on_button_press)

        # Flush and close writer
        self._writer.close()

        self._started = False
        logger.info(f"EventStoreService stopped: {self._seq} events processed")

    def flush(self) -> list | None:
        """Manually flush buffered events"""
        return self._writer.flush()

    def _next_seq(self) -> int:
        """Get next sequence number (thread-safe)"""
        with self._seq_lock:
            self._seq += 1
            return self._seq

    @staticmethod
    def _unwrap_event_payload(wrapped: Any) -> dict[str, Any] | None:
        """
        Unwrap event payload from EventBus and BrowserBridge wrappers.

        Handles three known formats:
        1. Already-unwrapped dict: {"event": "...", "data": {...}, ...}
           Returns: same dict

        2. EventBus + BrowserBridge double-wrapped: {"name": "...", "data": {"data": cdp_event}}
           Returns: cdp_event dict (inner "data")

        3. BrowserBridge-only wrapped: {"data": {"event": "...", "data": {...}, ...}}
           Returns: inner dict containing event details

        Args:
            wrapped: Raw event payload from EventBus subscription

        Returns:
            Unwrapped event dict with "event", "data", etc. fields, or None if invalid

        Note:
            The double-wrapping occurs because:
            - BrowserBridge publishes: {"data": cdp_event}
            - EventBus wraps it as: {"name": event_type, "data": bridge_payload}
            - Result: {"name": event_type, "data": {"data": cdp_event}}
        """
        # Validate input is dict
        if not isinstance(wrapped, dict):
            logger.warning(f"_unwrap_event_payload: Expected dict, got {type(wrapped)}")
            return None

        # Check if already unwrapped (has "event" field at top level)
        if "event" in wrapped:
            return wrapped

        # Try unwrapping one layer (could be EventBus or BrowserBridge wrapper)
        outer_data = wrapped.get("data")
        if outer_data is None or not isinstance(outer_data, dict):
            logger.warning(
                f"_unwrap_event_payload: Invalid first wrapper layer, got {type(outer_data)}"
            )
            return None

        # Check if outer_data already has "event" field (BrowserBridge-only case)
        if "event" in outer_data:
            return outer_data

        # Try unwrapping second layer (EventBus + BrowserBridge double-wrapped)
        data = outer_data.get("data")
        if data is None or not isinstance(data, dict):
            logger.warning(f"_unwrap_event_payload: Invalid second wrapper layer, got {type(data)}")
            return None

        return data

    def _on_ws_raw_event(self, wrapped: dict[str, Any]) -> None:
        """Handle raw WebSocket event"""
        # Early return if recording is paused
        if self._paused:
            return

        try:
            # Unwrap event payload from EventBus/BrowserBridge wrappers
            data = self._unwrap_event_payload(wrapped)
            if data is None:
                return

            # Extract event details
            event_name = data.get("event")
            if not event_name:
                logger.warning("WS_RAW_EVENT: Missing event name")
                return

            event_data = data.get("data") or {}  # Handle None value explicitly
            source_str = data.get("source", "public_ws")
            game_id = data.get("game_id") or (
                event_data.get("gameId") if isinstance(event_data, dict) else None
            )

            source = EventSource.CDP if source_str == "cdp" else EventSource.PUBLIC_WS

            # Write raw ws_event
            envelope = EventEnvelope.from_ws_event(
                event_name=event_name,
                data=event_data,
                source=source,
                session_id=self._session_id,
                seq=self._next_seq(),
                game_id=game_id,
            )
            self._writer.write(envelope)
            self._total_events_recorded += 1

            # TRAINING DATA: Extract complete games from gameHistory
            if event_name == "gameStateUpdate" and isinstance(event_data, dict):
                game_history = event_data.get("gameHistory", [])

                if game_history:
                    # Rug event! Capture all complete games (with deduplication)
                    new_games = []
                    for game in game_history:
                        # gameHistory games use "id" field, not "gameId"
                        gid = game.get("id") or game.get("gameId")
                        if gid and gid not in self._recorded_game_ids:
                            new_games.append(game)
                            self._recorded_game_ids.add(gid)

                    if new_games:
                        logger.info(
                            f"Capturing {len(new_games)} NEW complete games from gameHistory"
                        )

                        for game in new_games:
                            game_envelope = EventEnvelope.from_complete_game(
                                game_data=game,
                                source=source,
                                session_id=self._session_id,
                                seq=self._next_seq(),
                            )
                            self._writer.write(game_envelope)
                            self._total_events_recorded += 1

                        # Count sidebets for logging
                        total_sidebets = sum(len(g.get("globalSidebets", [])) for g in new_games)
                        total_ticks = sum(len(g.get("prices", [])) for g in new_games)
                        logger.info(
                            f"Captured training data: {len(new_games)} games, "
                            f"{total_sidebets} sidebets, {total_ticks} ticks"
                        )

        except Exception as e:
            logger.error(f"Error handling WS_RAW_EVENT: {e}")

    def _on_game_tick(self, wrapped: dict[str, Any]) -> None:
        """Handle game tick event"""
        # Early return if recording is paused
        if self._paused:
            return

        try:
            # EventBus wraps data: {"name": event.value, "data": actual_data}
            data = wrapped.get("data", wrapped)

            tick = data.get("tick", 0)
            price_raw = data.get("price", data.get("multiplier", 1.0))
            game_id = data.get("gameId", data.get("game_id", "unknown"))

            # Convert price to Decimal
            if isinstance(price_raw, Decimal):
                price = price_raw
            else:
                price = Decimal(str(price_raw))

            envelope = EventEnvelope.from_game_tick(
                tick=tick,
                price=price,
                data=data,
                source=EventSource.PUBLIC_WS,
                session_id=self._session_id,
                seq=self._next_seq(),
                game_id=game_id,
            )

            self._writer.write(envelope)
            self._total_events_recorded += 1

        except Exception as e:
            logger.error(f"Error handling GAME_TICK: {e}")

    def _on_player_update(self, wrapped: dict[str, Any]) -> None:
        """Handle player update event"""
        # Early return if recording is paused
        if self._paused:
            return

        try:
            # EventBus wraps data: {"name": event.value, "data": actual_data}
            data = wrapped.get("data", wrapped)

            game_id = data.get("gameId", data.get("game_id", "unknown"))
            player_id = data.get("playerId", data.get("player_id", "unknown"))
            username = data.get("username")

            # Extract cash and position
            cash_raw = data.get("cash", data.get("balance"))
            position_raw = data.get("positionQty", data.get("position_qty"))

            cash = Decimal(str(cash_raw)) if cash_raw is not None else None
            position_qty = Decimal(str(position_raw)) if position_raw is not None else None

            envelope = EventEnvelope.from_server_state(
                data=data,
                source=EventSource.PUBLIC_WS,
                session_id=self._session_id,
                seq=self._next_seq(),
                game_id=game_id,
                player_id=player_id,
                username=username,
                cash=cash,
                position_qty=position_qty,
            )

            self._writer.write(envelope)
            self._total_events_recorded += 1

        except Exception as e:
            logger.error(f"Error handling PLAYER_UPDATE: {e}")

    def _on_trade_buy(self, data: dict[str, Any]) -> None:
        """Handle buy trade event"""
        if self._paused:
            return
        self._handle_trade_action("buy", data)

    def _on_trade_sell(self, data: dict[str, Any]) -> None:
        """Handle sell trade event"""
        if self._paused:
            return
        self._handle_trade_action("sell", data)

    def _on_trade_sidebet(self, data: dict[str, Any]) -> None:
        """Handle sidebet trade event"""
        if self._paused:
            return
        self._handle_trade_action("sidebet", data)

    def _on_trade_confirmed(self, wrapped: dict[str, Any]) -> None:
        """Handle trade confirmation event with latency tracking"""
        if self._paused:
            return

        try:
            # EventBus wraps data: {"name": event.value, "data": actual_data}
            data = wrapped.get("data", wrapped)

            envelope = EventEnvelope.from_player_action(
                action_type="trade_confirmed",
                data=data,
                source=EventSource.UI,
                session_id=self._session_id,
                seq=self._next_seq(),
                game_id=data.get("gameId"),
                player_id=data.get("playerId"),
                username=data.get("username"),
            )

            self._writer.write(envelope)
            self._total_events_recorded += 1

        except Exception as e:
            logger.error(f"Error handling TRADE_CONFIRMED: {e}")

    def _handle_trade_action(self, action_type: str, wrapped: dict[str, Any]) -> None:
        """Common handler for trade actions"""
        try:
            # EventBus wraps data: {"name": event.value, "data": actual_data}
            data = wrapped.get("data", wrapped)

            game_id = data.get("gameId", data.get("game_id"))
            player_id = data.get("playerId", data.get("player_id"))
            username = data.get("username")

            envelope = EventEnvelope.from_player_action(
                action_type=action_type,
                data=data,
                source=EventSource.UI,
                session_id=self._session_id,
                seq=self._next_seq(),
                game_id=game_id,
                player_id=player_id,
                username=username,
            )

            self._writer.write(envelope)
            self._total_events_recorded += 1

        except Exception as e:
            logger.error(f"Error handling trade action {action_type}: {e}")

    def _on_button_press(self, wrapped: dict[str, Any]) -> None:
        """
        Handle ButtonEvent for RL training data (Phase B).

        ButtonEvents capture human button presses with full game context
        for training reinforcement learning models.
        """
        # Early return if recording is paused
        if self._paused:
            return

        try:
            # EventBus wraps data: {"name": event.value, "data": actual_data}
            data = wrapped.get("data", wrapped)

            # Extract button event fields
            button_id = data.get("button_id", "unknown")
            button_category = data.get("button_category", "unknown")
            game_id = data.get("game_id")
            tick = data.get("tick")
            price = data.get("price")
            sequence_id = data.get("sequence_id")
            sequence_position = data.get("sequence_position")

            envelope = EventEnvelope.from_button_event(
                button_id=button_id,
                button_category=button_category,
                data=data,
                source=EventSource.UI,
                session_id=self._session_id,
                seq=self._next_seq(),
                game_id=game_id,
                tick=tick,
                price=price,
                sequence_id=sequence_id,
                sequence_position=sequence_position,
            )

            self._writer.write(envelope)
            self._total_events_recorded += 1
            logger.debug(
                f"ButtonEvent stored: {button_id} tick={tick} seq={sequence_id[:8] if sequence_id else 'N/A'}"
            )

        except Exception as e:
            logger.error(f"Error handling BUTTON_PRESS: {e}")

    def __enter__(self) -> "EventStoreService":
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        self.stop()
