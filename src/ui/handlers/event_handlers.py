"""
Event handlers for MainWindow (game tick, trades, file loaded, etc).
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class EventHandlersMixin:
    """Mixin providing event handler functionality for MainWindow."""

    def _setup_event_handlers(self: "MainWindow"):
        """Setup event bus subscriptions"""
        from services.event_bus import Events

        self.event_bus.subscribe(Events.GAME_TICK, self._handle_game_tick)
        self.event_bus.subscribe(Events.TRADE_EXECUTED, self._handle_trade_executed)
        self.event_bus.subscribe(Events.TRADE_FAILED, self._handle_trade_failed)
        self.event_bus.subscribe(Events.FILE_LOADED, self._handle_file_loaded)
        self.event_bus.subscribe(Events.WS_SOURCE_CHANGED, self._handle_ws_source_changed)
        self.event_bus.subscribe(Events.PLAYER_IDENTITY, self._handle_player_identity)
        self.event_bus.subscribe(Events.PLAYER_UPDATE, self._handle_player_update)

        from core.game_state import StateEvents

        self.state.subscribe(StateEvents.BALANCE_CHANGED, self._handle_balance_changed)
        self.state.subscribe(StateEvents.POSITION_OPENED, self._handle_position_opened)
        self.state.subscribe(StateEvents.POSITION_CLOSED, self._handle_position_closed)
        self.state.subscribe(
            StateEvents.SELL_PERCENTAGE_CHANGED, self._handle_sell_percentage_changed
        )
        self.state.subscribe(StateEvents.POSITION_REDUCED, self._handle_position_reduced)

    def _handle_game_tick(self: "MainWindow", event):
        """Handle game tick from EventBus (live mode).

        Bridges EventBus GAME_TICK events to the UI update logic.
        """
        from models import GameTick

        data = event.get("data", {})
        if not data:
            return

        # Convert dict to GameTick if needed
        if isinstance(data, dict):
            try:
                tick = GameTick(
                    tick=data.get("tick", data.get("tickIndex", 0)),
                    price=float(data.get("price", data.get("currentPrice", 1.0))),
                    phase=data.get("phase", "UNKNOWN"),
                    rugged=data.get("rugged", False),
                    seed=data.get("seed"),
                    game_id=data.get("game_id", data.get("gameId")),
                )
            except Exception as e:
                logger.debug(f"Failed to parse game tick: {e}")
                return
        elif isinstance(data, GameTick):
            tick = data
        else:
            return

        # Route to the existing tick processing logic
        self._process_tick_ui(tick, 0, 0)

    def _handle_trade_executed(self: "MainWindow", event):
        """Handle successful trade"""
        self.log(f"Trade executed: {event.get('data')}")

    def _handle_trade_failed(self: "MainWindow", event):
        """Handle failed trade"""
        self.log(f"Trade failed: {event.get('data')}")

    def _handle_file_loaded(self: "MainWindow", event):
        """Handle file loaded event"""
        files = event.get("data", {}).get("files", [])
        if files:
            self.log(f"Found {len(files)} game files")
            if hasattr(self, "replay_controller"):
                self.replay_controller.load_game_file(files[0])

    def _handle_ws_source_changed(self: "MainWindow", event):
        """Handle WebSocket source change event (CDP vs fallback)."""
        from services.event_source_manager import EventSource

        data = event.get("data", {})
        source_str = data.get("source", "")

        if source_str == "cdp":
            source = EventSource.CDP
        elif source_str == "fallback":
            source = EventSource.FALLBACK
        else:
            source = None

        logger.info(f"WebSocket source changed: {source_str}")
        self._update_source_indicator(source)

    def _handle_position_opened(self: "MainWindow", data):
        """Handle position opened (thread-safe via TkDispatcher)"""
        entry_price = data.get("entry_price", 0)
        self.ui_dispatcher.submit(lambda: self.log(f"Position opened at {entry_price:.4f}"))

    def _handle_position_closed(self: "MainWindow", data):
        """Handle position closed (thread-safe via TkDispatcher)"""
        pnl = data.get("pnl_sol", 0)
        self.ui_dispatcher.submit(lambda: self.log(f"Position closed - P&L: {pnl:+.4f} SOL"))

    def _handle_sell_percentage_changed(self: "MainWindow", data):
        """Handle sell percentage changed (Phase 8.2, thread-safe via TkDispatcher)"""
        new_percentage = data.get("new", 1.0)
        self.ui_dispatcher.submit(
            lambda: self.trading_controller.highlight_percentage_button(float(new_percentage))
            if hasattr(self, "trading_controller")
            else None
        )

    def _handle_position_reduced(self: "MainWindow", data):
        """Handle partial position close (Phase 8.2, thread-safe via TkDispatcher)"""
        percentage = data.get("percentage", 0)
        pnl = data.get("pnl_sol", 0)
        remaining = data.get("remaining_amount", 0)
        self.ui_dispatcher.submit(
            lambda: self.log(
                f"Position reduced ({percentage * 100:.0f}%) - P&L: {pnl:+.4f} SOL, Remaining: {remaining:.4f} SOL"
            )
        )

    def _update_capture_stats(self: "MainWindow"):
        """Update capture stats display (Phase 12D)."""
        try:
            if hasattr(self, "event_store_service") and self.event_store_service:
                session_id = self.event_store_service.session_id[:8]
                event_count = self.event_store_service.event_count
                text = f"Session: {session_id} | Events: {event_count}"
                self.capture_stats_label.config(text=text)
        except Exception as e:
            logger.debug(f"Error updating capture stats: {e}")

        self.root.after(1000, self._update_capture_stats)
