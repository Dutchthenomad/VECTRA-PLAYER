"""
Toast handlers for MainWindow - EventBus-driven toast notifications.

Subscribes to EventBus events and displays appropriate toast notifications
thread-safely via ui_dispatcher.

Issue #138: Migrate Toast Notifications to Socket Events
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class ToastHandlersMixin:
    """Mixin providing EventBus-driven toast notifications for MainWindow."""

    # Default toast preferences (can be overridden via config)
    DEFAULT_TOAST_PREFERENCES = {
        "ws_connected": True,
        "ws_disconnected": True,
        "ws_error": True,
        "game_start": True,
        "game_end": True,
        "game_rug": True,
        "trade_executed": False,  # Controllers handle these directly
        "trade_failed": False,  # Controllers handle these directly
        "player_update": False,  # Too noisy for every update
    }

    def _setup_toast_handlers(self: "MainWindow"):
        """Setup EventBus subscriptions for toast notifications."""
        from services.event_bus import Events

        # Load toast preferences from config (or use defaults)
        self._toast_preferences = getattr(
            self.config, "TOAST_PREFERENCES", self.DEFAULT_TOAST_PREFERENCES.copy()
        )

        # WebSocket connection events
        self.event_bus.subscribe(Events.WS_CONNECTED, self._on_ws_connected_toast)
        self.event_bus.subscribe(Events.WS_DISCONNECTED, self._on_ws_disconnected_toast)
        self.event_bus.subscribe(Events.WS_ERROR, self._on_ws_error_toast)

        # Game lifecycle events
        self.event_bus.subscribe(Events.GAME_START, self._on_game_start_toast)
        self.event_bus.subscribe(Events.GAME_END, self._on_game_end_toast)
        self.event_bus.subscribe(Events.GAME_RUG, self._on_game_rug_toast)

        logger.debug("Toast handlers registered with EventBus")

    def _is_toast_enabled(self: "MainWindow", toast_type: str) -> bool:
        """Check if a specific toast type is enabled."""
        return self._toast_preferences.get(toast_type, True)

    def _show_toast_safe(self: "MainWindow", message: str, msg_type: str = "info"):
        """Show toast notification thread-safely via ui_dispatcher."""
        if hasattr(self, "toast") and self.toast is not None:
            self.ui_dispatcher.submit(lambda: self.toast.show(message, msg_type))
        else:
            logger.warning(f"Toast not initialized, message dropped: {message}")

    # ========================================================================
    # WebSocket Connection Handlers
    # ========================================================================

    def _on_ws_connected_toast(self: "MainWindow", event):
        """Handle WebSocket connected event."""
        if not self._is_toast_enabled("ws_connected"):
            return

        data = event.get("data", {})
        source = data.get("source", "live feed")
        self._show_toast_safe(f"Connected to {source}", "success")

    def _on_ws_disconnected_toast(self: "MainWindow", event):
        """Handle WebSocket disconnected event."""
        if not self._is_toast_enabled("ws_disconnected"):
            return

        data = event.get("data", {})
        reason = data.get("reason", "")
        message = "Disconnected from server"
        if reason:
            message = f"Disconnected: {reason}"
        self._show_toast_safe(message, "warning")

    def _on_ws_error_toast(self: "MainWindow", event):
        """Handle WebSocket error event."""
        if not self._is_toast_enabled("ws_error"):
            return

        data = event.get("data", {})
        error = data.get("error", "Unknown error")
        self._show_toast_safe(f"Connection error: {error}", "error")

    # ========================================================================
    # Game Lifecycle Handlers
    # ========================================================================

    def _on_game_start_toast(self: "MainWindow", event):
        """Handle game start event."""
        if not self._is_toast_enabled("game_start"):
            return

        data = event.get("data", {})
        game_id = data.get("game_id", data.get("gameId", ""))
        if game_id:
            self._show_toast_safe(f"New game started: {game_id[:8]}", "info")
        else:
            self._show_toast_safe("New game started", "info")

    def _on_game_end_toast(self: "MainWindow", event):
        """Handle game end event."""
        if not self._is_toast_enabled("game_end"):
            return

        data = event.get("data", {})
        final_price = data.get("final_price", data.get("finalPrice", 0))
        rugged = data.get("rugged", False)

        if rugged:
            # Let _on_game_rug_toast handle rugged games
            return

        if final_price > 0:
            self._show_toast_safe(f"Game ended at {final_price:.2f}x", "info")
        else:
            self._show_toast_safe("Game ended", "info")

    def _on_game_rug_toast(self: "MainWindow", event):
        """Handle game rug event."""
        if not self._is_toast_enabled("game_rug"):
            return

        data = event.get("data", {})
        final_price = data.get("price", data.get("final_price", 0))

        if final_price > 0:
            self._show_toast_safe(f"RUGGED at {final_price:.2f}x!", "error")
        else:
            self._show_toast_safe("RUGGED!", "error")

    # ========================================================================
    # Toast Preference Management
    # ========================================================================

    def set_toast_preference(self: "MainWindow", toast_type: str, enabled: bool):
        """Enable or disable a specific toast type."""
        if not hasattr(self, "_toast_preferences"):
            self._toast_preferences = self.DEFAULT_TOAST_PREFERENCES.copy()
        self._toast_preferences[toast_type] = enabled
        logger.debug(f"Toast preference '{toast_type}' set to {enabled}")

    def get_toast_preferences(self: "MainWindow") -> dict:
        """Get current toast preferences."""
        if not hasattr(self, "_toast_preferences"):
            self._toast_preferences = self.DEFAULT_TOAST_PREFERENCES.copy()
        return self._toast_preferences.copy()
