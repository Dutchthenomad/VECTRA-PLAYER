"""
Browser Service - Flask integration for BrowserBridge.

Wraps the BrowserBridge singleton to provide:
1. HTTP API endpoints for browser control
2. EventBus → SocketIO forwarding for real-time updates
3. Game state tracking for UI display
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from services.event_bus import Events, event_bus

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Current game state from WebSocket events."""

    game_id: str = ""
    tick_count: int = 0
    price: float = 1.0
    phase: str = "UNKNOWN"
    active: bool = False
    rugged: bool = False
    cooldown_timer: int = 0
    username: str = ""
    balance: float = 0.0
    last_update: float = 0.0
    # Tracked bet amount (optimistic - may drift from actual browser value)
    bet_amount: float = 0.01


class BrowserService:
    """
    Flask-compatible wrapper for BrowserBridge.

    Provides synchronous methods for Flask endpoints while managing
    the async BrowserBridge internally.
    """

    def __init__(self, socketio=None):
        """
        Initialize browser service.

        Args:
            socketio: Flask-SocketIO instance for real-time event forwarding
        """
        self._bridge = None
        self._socketio = socketio
        self._game_state = GameState()
        self._lock = threading.Lock()
        self._bridge_lock = threading.Lock()  # Separate lock for bridge creation
        self._connected = False

        # Subscribe to EventBus for game state updates
        self._setup_event_subscriptions()

        logger.info("BrowserService initialized")

    def _setup_event_subscriptions(self):
        """Subscribe to EventBus events for real-time updates."""
        # Subscribe to raw WebSocket events
        event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_event, weak=False)

        # Subscribe to player updates
        event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update, weak=False)

        logger.debug("BrowserService subscribed to EventBus events")

    def _get_bridge(self):
        """Lazy-load BrowserBridge to avoid circular imports (thread-safe)."""
        # Double-checked locking pattern for thread safety
        if self._bridge is None:
            with self._bridge_lock:
                # Check again inside lock to prevent race condition
                if self._bridge is None:
                    from browser.bridge import BrowserBridge

                    bridge = BrowserBridge()

                    # Set up status change callback
                    def on_status_change(status):
                        from browser.bridge import BridgeStatus

                        self._connected = status == BridgeStatus.CONNECTED

                        # Emit status to SocketIO clients
                        if self._socketio:
                            self._socketio.emit(
                                "browser_status",
                                {
                                    "connected": self._connected,
                                    "status": status.value,
                                },
                            )

                    bridge.on_status_change = on_status_change
                    self._bridge = bridge

        return self._bridge

    # =========================================================================
    # PUBLIC API METHODS
    # =========================================================================

    def connect(self) -> dict[str, Any]:
        """
        Connect to Chrome browser via CDP.

        Returns:
            Dict with status info
        """
        bridge = self._get_bridge()

        if bridge.is_connected():
            return {
                "success": True,
                "message": "Already connected",
                "connected": True,
            }

        try:
            bridge.connect()

            # Wait briefly for connection to establish
            time.sleep(0.5)

            return {
                "success": True,
                "message": "Connection initiated",
                "connected": bridge.is_connected(),
            }
        except Exception as e:
            logger.error(f"Browser connect failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "connected": False,
            }

    def disconnect(self) -> dict[str, Any]:
        """
        Disconnect from browser (keeps Chrome running).

        Returns:
            Dict with status info
        """
        bridge = self._get_bridge()

        if not bridge.is_connected():
            return {
                "success": True,
                "message": "Already disconnected",
                "connected": False,
            }

        try:
            bridge.disconnect()
            return {
                "success": True,
                "message": "Disconnected",
                "connected": False,
            }
        except Exception as e:
            logger.error(f"Browser disconnect failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_status(self) -> dict[str, Any]:
        """
        Get current browser and game state.

        Returns:
            Dict with connection status and game state
        """
        bridge = self._get_bridge()

        with self._lock:
            return {
                "connected": bridge.is_connected(),
                "status": bridge.status.value if bridge.status else "disconnected",
                "game": {
                    "game_id": self._game_state.game_id[:8] if self._game_state.game_id else "",
                    "tick_count": self._game_state.tick_count,
                    "price": self._game_state.price,
                    "phase": self._game_state.phase,
                    "active": self._game_state.active,
                    "rugged": self._game_state.rugged,
                },
                "player": {
                    "username": self._game_state.username,
                    "balance": self._game_state.balance,
                },
                "bet_amount": self._game_state.bet_amount,
                "last_update": self._game_state.last_update,
            }

    def is_connected(self) -> bool:
        """Check if browser is connected."""
        return self._get_bridge().is_connected()

    # =========================================================================
    # TRADING ACTIONS
    # =========================================================================

    def click_buy(self) -> dict[str, Any]:
        """Execute BUY click in browser."""
        return self._do_click("buy")

    def click_sell(self) -> dict[str, Any]:
        """Execute SELL click in browser."""
        return self._do_click("sell")

    def click_sidebet(self) -> dict[str, Any]:
        """Execute SIDEBET click in browser."""
        return self._do_click("sidebet")

    def click_increment(self, amount: float) -> dict[str, Any]:
        """
        Click increment button to adjust bet amount.

        Args:
            amount: One of 0.001, 0.01, 0.1, 1.0
        """
        button_map = {
            0.001: "+0.001",
            0.01: "+0.01",
            0.1: "+0.1",
            1.0: "+1",
        }
        button = button_map.get(amount)
        if not button:
            return {"success": False, "error": f"Invalid increment: {amount}"}

        result = self._do_click(button)
        if result.get("success"):
            with self._lock:
                self._game_state.bet_amount += amount
                result["bet_amount"] = self._game_state.bet_amount
        return result

    def click_percentage(self, pct: int) -> dict[str, Any]:
        """
        Click percentage button for sell amount.

        Args:
            pct: One of 10, 25, 50, 100
        """
        pct_map = {10: 0.1, 25: 0.25, 50: 0.5, 100: 1.0}
        ratio = pct_map.get(pct)
        if ratio is None:
            return {"success": False, "error": f"Invalid percentage: {pct}"}

        bridge = self._get_bridge()
        if not bridge.is_connected():
            return {"success": False, "error": "Browser not connected"}

        bridge.on_percentage_clicked(ratio)
        return {"success": True, "action": f"{pct}%"}

    def click_clear(self) -> dict[str, Any]:
        """Clear bet to 0."""
        result = self._do_click("X")
        if result.get("success"):
            with self._lock:
                self._game_state.bet_amount = 0.0
                result["bet_amount"] = self._game_state.bet_amount
        return result

    def click_half(self) -> dict[str, Any]:
        """Halve current bet."""
        result = self._do_click("1/2")
        if result.get("success"):
            with self._lock:
                self._game_state.bet_amount /= 2
                result["bet_amount"] = self._game_state.bet_amount
        return result

    def click_double(self) -> dict[str, Any]:
        """Double current bet."""
        result = self._do_click("X2")
        if result.get("success"):
            with self._lock:
                self._game_state.bet_amount *= 2
                result["bet_amount"] = self._game_state.bet_amount
        return result

    def click_max(self) -> dict[str, Any]:
        """Set bet to max balance."""
        result = self._do_click("MAX")
        if result.get("success"):
            with self._lock:
                # Set to player balance (max bet)
                self._game_state.bet_amount = self._game_state.balance
                result["bet_amount"] = self._game_state.bet_amount
        return result

    def _do_click(self, action: str) -> dict[str, Any]:
        """
        Execute a click action.

        Args:
            action: Button identifier (buy, sell, sidebet, +0.001, etc.)
        """
        bridge = self._get_bridge()

        if not bridge.is_connected():
            return {
                "success": False,
                "error": "Browser not connected",
            }

        try:
            action_upper = action.upper()

            if action_upper == "BUY":
                bridge.on_buy_clicked()
            elif action_upper == "SELL":
                bridge.on_sell_clicked()
            elif action_upper == "SIDEBET":
                bridge.on_sidebet_clicked()
            else:
                # Increment/utility buttons
                bridge.on_increment_clicked(action)

            return {
                "success": True,
                "action": action,
            }
        except Exception as e:
            logger.error(f"Click action failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_ws_event(self, event: dict[str, Any]):
        """Handle raw WebSocket events from EventBus."""
        event_type = event.get("event")
        data = event.get("data", {})

        if event_type == "gameStateUpdate":
            self._handle_game_state(data)
        elif event_type == "usernameStatus":
            self._handle_username(data)
        elif event_type == "playerUpdate":
            self._handle_player_update_data(data)

    def _on_player_update(self, data: dict[str, Any]):
        """Handle player update events."""
        self._handle_player_update_data(data)

    def _handle_game_state(self, data: dict[str, Any]):
        """Update game state from gameStateUpdate event."""
        with self._lock:
            self._game_state.game_id = data.get("gameId", "")
            self._game_state.tick_count = data.get("tickCount", 0)
            self._game_state.price = float(data.get("price", 1.0))
            self._game_state.active = data.get("active", False)
            self._game_state.rugged = data.get("rugged", False)
            self._game_state.cooldown_timer = data.get("cooldownTimer", 0)
            self._game_state.last_update = time.time()

            # Detect phase from flags
            if self._game_state.cooldown_timer > 0:
                self._game_state.phase = "COOLDOWN"
            elif not self._game_state.active:
                self._game_state.phase = "PRESALE"
            elif self._game_state.rugged:
                self._game_state.phase = "RUGGED"
            else:
                self._game_state.phase = "ACTIVE"

        # Forward to SocketIO clients
        if self._socketio:
            self._socketio.emit(
                "game_state",
                {
                    "game_id": self._game_state.game_id[:8] if self._game_state.game_id else "",
                    "tick_count": self._game_state.tick_count,
                    "price": self._game_state.price,
                    "phase": self._game_state.phase,
                    "active": self._game_state.active,
                    "rugged": self._game_state.rugged,
                },
            )

    def _handle_username(self, data: dict[str, Any]):
        """Update username from usernameStatus event."""
        with self._lock:
            self._game_state.username = data.get("username", "")

        if self._socketio:
            self._socketio.emit(
                "player_info",
                {
                    "username": self._game_state.username,
                    "balance": self._game_state.balance,
                },
            )

    def _handle_player_update_data(self, data: dict[str, Any]):
        """Update player info from playerUpdate event."""
        with self._lock:
            if "cash" in data:
                self._game_state.balance = float(data.get("cash", 0))
            elif "balance" in data:
                self._game_state.balance = float(data.get("balance", 0))

        if self._socketio:
            self._socketio.emit(
                "player_info",
                {
                    "username": self._game_state.username,
                    "balance": self._game_state.balance,
                },
            )


# =============================================================================
# MODULE-LEVEL SINGLETON (Thread-Safe)
# =============================================================================

_browser_service: BrowserService | None = None
_browser_service_lock = threading.Lock()


def get_browser_service(socketio=None) -> BrowserService:
    """Get or create the BrowserService singleton (thread-safe)."""
    global _browser_service

    # Double-checked locking pattern
    if _browser_service is None:
        with _browser_service_lock:
            if _browser_service is None:
                _browser_service = BrowserService(socketio)
    elif socketio and _browser_service._socketio is None:
        with _browser_service_lock:
            if _browser_service._socketio is None:
                _browser_service._socketio = socketio

    return _browser_service
