"""
Player identity and server state handlers for MainWindow.
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class PlayerHandlersMixin:
    """Mixin providing player/server state handler functionality for MainWindow."""

    def _handle_player_identity(self: "MainWindow", event):
        """Handle player identity event from WebSocket (usernameStatus)."""
        data = event.get("data", {})
        username = data.get("username")
        player_id = data.get("player_id")

        if username:
            self.server_username = username
            self.server_player_id = player_id
            self.server_authenticated = True

            def update_profile_ui():
                self.player_profile_label.config(
                    text=f"\U0001f464 {username}",  # 👤
                    fg="#00ff88",
                )
                logger.info(f"Player authenticated: {username}")

            self.ui_dispatcher.submit(update_profile_ui)

    def _handle_player_update(self: "MainWindow", event):
        """Handle player update event from WebSocket (playerUpdate)."""
        data = event.get("data", {})
        server_state = data.get("server_state")

        if server_state:
            cash = getattr(server_state, "cash", None)
            if cash is not None:
                self.server_balance = Decimal(str(cash))

                drifts = self.state.reconcile_with_server(server_state)
                if drifts:
                    logger.info(f"State reconciled with server: {list(drifts.keys())}")

                self._update_balance_from_live_state()

    def _update_balance_from_live_state(self: "MainWindow"):
        """Update balance display using server-authoritative LiveStateProvider."""
        if not hasattr(self, "live_state_provider") or not self.balance_locked:
            return

        if self.live_state_provider.is_connected:
            server_cash = self.live_state_provider.cash
            username = self.live_state_provider.username or "Unknown"

            def update_live():
                self.balance_label.config(
                    text=f"WALLET: {server_cash:.4f} SOL",
                    fg="#00ff88",
                )
                logger.debug(
                    f"Balance updated from LiveStateProvider: {server_cash} (LIVE: {username})"
                )

            self.ui_dispatcher.submit(update_live)
        else:
            local_balance = self.state.get("balance")

            def update_local():
                self.balance_label.config(
                    text=f"WALLET: {local_balance:.4f} SOL",
                    fg="#888888",
                )
                logger.debug(f"Balance updated from GameState: {local_balance} (LOCAL)")

            self.ui_dispatcher.submit(update_local)

    def _reset_server_state(self: "MainWindow"):
        """Reset server state tracking (called on disconnect)."""
        self.server_username = None
        self.server_player_id = None
        self.server_balance = None
        self.server_authenticated = False

        def reset_profile_ui():
            self.player_profile_label.config(
                text="\U0001f464 Not Authenticated",  # 👤
                fg="#666666",
            )
            self._update_balance_from_live_state()

        self.ui_dispatcher.submit(reset_profile_ui)

    def get_latest_server_state(self: "MainWindow"):
        """Get the latest server state from WebSocket feed (Phase 11)."""
        if not self.live_feed_connected or not self.live_feed:
            return None
        return self.live_feed.get_last_server_state()

    def _update_source_indicator(self: "MainWindow", source):
        """Update event source indicator with LIVE status."""
        from services.event_source_manager import EventSource

        live_status = ""
        if hasattr(self, "live_state_provider") and self.live_state_provider.is_connected:
            raw_username = self.live_state_provider.username or "Unknown"
            username = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw_username)[:20]
            live_status = f" | LIVE: {username}"

        if source == EventSource.CDP:
            text = f"\U0001f7e2 CDP: Authenticated{live_status}"  # 🟢
            color = "#00ff88"
        elif source == EventSource.FALLBACK:
            text = f"\U0001f7e1 Fallback: Public{live_status}"  # 🟡
            color = "#ffcc00"
        else:
            text = "\U0001f534 No Source"  # 🔴
            color = "#ff4444"

        def update():
            self.source_label.config(text=text, foreground=color)

        self.ui_dispatcher.submit(update)
