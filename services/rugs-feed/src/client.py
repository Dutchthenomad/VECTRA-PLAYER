"""
RugsFeedClient - Direct Socket.IO connection to rugs.fun backend.

Captures raw events including:
- gameStateUpdate with provablyFair.serverSeed
- standard/newTrade for timing analysis
- Sidebet events

Broadcasts all events to downstream subscribers via WebSocket.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import socketio

if TYPE_CHECKING:
    from .broadcaster import RawEventBroadcaster

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


@dataclass
class GameHistoryEntry:
    """A complete game from gameHistory (captured on rug)."""

    game_id: str
    timestamp_ms: int
    peak_multiplier: float
    rugged: bool
    server_seed: str | None
    server_seed_hash: str | None
    global_trades: list[dict]
    global_sidebets: list[dict]
    game_version: str | None = None


class RugsFeedClient:
    """
    Direct Socket.IO client for rugs.fun backend.

    Captures all game events for PRNG analysis, including:
    - Server seed reveals (provablyFair)
    - Game state updates with timestamps
    - Trade events for timing correlation

    Broadcasts all events to downstream WebSocket subscribers.
    Captures gameHistory on rug events (dual-broadcast deduplication).
    """

    def __init__(
        self,
        url: str = RUGS_BACKEND_URL,
        on_event: Callable[[CapturedEvent], None] | None = None,
        broadcaster: "RawEventBroadcaster | None" = None,
        on_game_history: Callable[[GameHistoryEntry], None] | None = None,
    ):
        """
        Initialize client.

        Args:
            url: Backend URL (default: https://backend.rugs.fun)
            on_event: Callback for captured events (storage)
            broadcaster: WebSocket broadcaster for downstream services
            on_game_history: Callback for complete game records from gameHistory
        """
        self._url = url
        self._on_event = on_event
        self._broadcaster = broadcaster
        self._on_game_history = on_game_history
        self._state = ConnectionState.DISCONNECTED
        self._sio: socketio.AsyncClient | None = None
        self._handlers: dict[str, Callable] = {}
        self._current_game_id: str | None = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Deduplication: track which gameHistory entries we've already captured
        # Server broadcasts gameHistory TWICE on rug (dual-broadcast mechanism)
        self._captured_game_ids: set[str] = set()
        # Limit memory usage - only track recent 100 games
        self._max_captured_ids = 100

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
        """Emit captured event to callback and broadcaster."""
        # Storage callback
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

        # Broadcast to downstream WebSocket subscribers
        if self._broadcaster:
            try:
                self._broadcaster.broadcast(event)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

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

        # Capture gameHistory when present
        # This happens during cooldown (active=False) after game ends
        # gameHistory contains complete game records with serverSeed
        if data.get("gameHistory"):
            await self._capture_game_history(data)

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

    async def _capture_game_history(self, data: dict) -> None:
        """
        Capture complete game records from gameHistory.

        Called whenever gameHistory is present in the event data.
        Server broadcasts gameHistory during cooldown phase (active=False).
        The dual-broadcast mechanism may send it twice - we deduplicate by game_id.

        gameHistory contains last 10 games with:
        - id, timestamp, peakMultiplier, rugged
        - provablyFair (serverSeed, serverSeedHash) - CRITICAL FOR PRNG
        - globalTrades, globalSidebets
        - gameVersion
        """
        game_history = data.get("gameHistory", [])
        if not game_history:
            return

        new_games = 0
        for game in game_history:
            game_id = game.get("id")
            if not game_id:
                continue

            # Deduplicate - skip if already captured
            if game_id in self._captured_game_ids:
                continue

            # Mark as captured
            self._captured_game_ids.add(game_id)

            # Memory management - keep only recent games
            if len(self._captured_game_ids) > self._max_captured_ids:
                # Remove oldest (first added)
                oldest = next(iter(self._captured_game_ids))
                self._captured_game_ids.discard(oldest)

            # Extract provablyFair data
            provably_fair = game.get("provablyFair", {})

            # Create GameHistoryEntry
            entry = GameHistoryEntry(
                game_id=game_id,
                timestamp_ms=game.get("timestamp", 0),
                peak_multiplier=game.get("peakMultiplier", 0.0),
                rugged=game.get("rugged", False),
                server_seed=provably_fair.get("serverSeed"),
                server_seed_hash=provably_fair.get("serverSeedHash"),
                global_trades=game.get("globalTrades", []),
                global_sidebets=game.get("globalSidebets", []),
                game_version=game.get("gameVersion"),
            )

            # Emit to callback
            if self._on_game_history:
                try:
                    self._on_game_history(entry)
                except Exception as e:
                    logger.error(f"Game history callback error: {e}")

            new_games += 1

        if new_games > 0:
            logger.info(f"Captured {new_games} new games from gameHistory")
