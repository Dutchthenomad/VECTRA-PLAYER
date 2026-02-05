"""
RugsFeedClient - Direct Socket.IO connection to rugs.fun backend.

Captures raw events including:
- gameStateUpdate with provablyFair.serverSeed
- standard/newTrade for timing analysis
- Sidebet events
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import socketio

logger = logging.getLogger(__name__)

RUGS_BACKEND_URL = "https://backend.rugs.fun"


class ConnectionState(Enum):
    """WebSocket connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class CapturedEvent:
    """A captured WebSocket event."""

    event_type: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    game_id: str | None = None
    raw_message: str | None = None


class RugsFeedClient:
    """
    Direct Socket.IO client for rugs.fun backend.

    Captures all game events for PRNG analysis, including:
    - Server seed reveals (provablyFair)
    - Game state updates with timestamps
    - Trade events for timing correlation
    """

    def __init__(
        self,
        url: str = RUGS_BACKEND_URL,
        on_event: Callable[[CapturedEvent], None] | None = None,
    ):
        """
        Initialize client.

        Args:
            url: Backend URL (default: https://backend.rugs.fun)
            on_event: Callback for captured events
        """
        self._url = url
        self._on_event = on_event
        self._state = ConnectionState.DISCONNECTED
        self._sio: socketio.AsyncClient | None = None
        self._handlers: dict[str, Callable] = {}
        self._current_game_id: str | None = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Register default handlers
        self._register_handlers()

    @property
    def url(self) -> str:
        """Get backend URL."""
        return self._url

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == ConnectionState.CONNECTED

    def _register_handlers(self) -> None:
        """Register Socket.IO event handlers."""
        self._handlers = {
            "gameStateUpdate": self._handle_game_state,
            "standard/newTrade": self._handle_trade,
            "currentSidebet": self._handle_sidebet,
            "currentSidebetResult": self._handle_sidebet_result,
            "usernameStatus": self._handle_identity,
            "playerUpdate": self._handle_player_update,
        }

    async def connect(self) -> None:
        """
        Connect to rugs.fun backend.

        Maintains connection with automatic reconnection.
        """
        self._state = ConnectionState.CONNECTING

        # Create Socket.IO client
        self._sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=self._max_reconnect_attempts,
            reconnection_delay=1,
            reconnection_delay_max=30,
            logger=False,
        )

        # Register connection handlers
        @self._sio.event
        async def connect():
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0
            logger.info(f"Connected to {self._url}")

        @self._sio.event
        async def disconnect():
            self._state = ConnectionState.DISCONNECTED
            logger.warning("Disconnected from backend")

        @self._sio.event
        async def connect_error(data):
            self._reconnect_attempts += 1
            logger.error(f"Connection error (attempt {self._reconnect_attempts}): {data}")

        # Register event handlers
        for event_name, handler in self._handlers.items():
            self._sio.on(event_name, handler)

        # Connect with query params
        try:
            await self._sio.connect(
                self._url,
                transports=["websocket", "polling"],
                headers={"Origin": "https://rugs.fun"},
            )
        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            logger.error(f"Failed to connect: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from backend."""
        if self._sio:
            await self._sio.disconnect()
        self._state = ConnectionState.DISCONNECTED

    async def wait(self) -> None:
        """Wait for connection to close."""
        if self._sio:
            await self._sio.wait()

    def _emit_event(self, event: CapturedEvent) -> None:
        """Emit captured event to callback."""
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    async def _handle_game_state(self, *args) -> None:
        """Handle gameStateUpdate event."""
        # Socket.IO can pass trace object + data
        data = args[-1] if args else {}

        game_id = data.get("gameId")
        self._current_game_id = game_id

        # Extract seed reveal (only present after rug)
        provably_fair = data.get("provablyFair", {})
        server_seed = provably_fair.get("serverSeed")

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data=data,
            game_id=game_id,
        )

        # Log seed reveals (critical for PRNG analysis)
        if server_seed and data.get("rugged"):
            logger.info(f"SEED REVEAL: game={game_id} seed={server_seed[:16]}...")

        self._emit_event(event)

    async def _handle_trade(self, *args) -> None:
        """Handle standard/newTrade event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="standard/newTrade",
            data=data,
            game_id=data.get("gameId"),
        )
        self._emit_event(event)

    async def _handle_sidebet(self, *args) -> None:
        """Handle currentSidebet event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="currentSidebet",
            data=data,
            game_id=data.get("gameId"),
        )
        self._emit_event(event)

    async def _handle_sidebet_result(self, *args) -> None:
        """Handle currentSidebetResult event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="currentSidebetResult",
            data=data,
            game_id=data.get("gameId"),
        )
        self._emit_event(event)

    async def _handle_identity(self, *args) -> None:
        """Handle usernameStatus event (auth confirmation)."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="usernameStatus",
            data=data,
        )
        logger.info(f"Identity confirmed: {data.get('username', 'unknown')}")
        self._emit_event(event)

    async def _handle_player_update(self, *args) -> None:
        """Handle playerUpdate event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="playerUpdate",
            data=data,
        )
        self._emit_event(event)
