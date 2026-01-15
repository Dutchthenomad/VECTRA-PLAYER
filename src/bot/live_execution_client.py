"""
LiveExecutionClient - Connects to Flask SocketIO and mirrors bets to browser.

This bridges the gap between:
- Flask process (paper trading, visualization)
- Alpha test process (browser control, real execution)

The Flask dashboard is the source of truth for trading decisions.
This client mirrors those decisions to real browser clicks when enabled.
"""

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import socketio

if TYPE_CHECKING:
    from bot.execution_bridge import BotExecutionBridge

logger = logging.getLogger(__name__)


class LiveExecutionClient:
    """
    SocketIO client that mirrors Flask paper trading to real execution.

    Flow:
    1. Connect to Flask SocketIO server
    2. Join live session (same session_id as Flask dashboard)
    3. Listen for live_tick events
    4. When bet placement detected, execute via browser if enabled
    """

    def __init__(
        self,
        flask_url: str = "http://localhost:5005",
        execution_bridge: Optional["BotExecutionBridge"] = None,
    ):
        self.flask_url = flask_url
        self.execution_bridge = execution_bridge
        self._enabled = False

        # SocketIO client
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self._setup_handlers()

        # Track state to detect new bets
        self._session_id: str | None = None
        self._last_bets_placed: set[int] = set()
        self._last_active_bets: list[dict] = []

        # Callbacks for UI updates
        self._on_tick_callback: Callable | None = None
        self._on_bet_callback: Callable | None = None

    def _setup_handlers(self):
        """Set up SocketIO event handlers."""

        @self.sio.event
        def connect():
            logger.info(f"Connected to Flask SocketIO at {self.flask_url}")

        @self.sio.event
        def disconnect():
            logger.warning("Disconnected from Flask SocketIO")

        @self.sio.on("live_joined")
        def on_live_joined(data):
            logger.info(f"Joined live session: {data.get('session_id')}")
            session = data.get("session", {})
            # Initialize tracking state
            self._last_bets_placed = set(session.get("bets_placed_this_game", []))
            self._last_active_bets = session.get("active_bets", [])

        @self.sio.on("live_tick")
        def on_live_tick(data):
            self._handle_tick(data)

        @self.sio.on("error")
        def on_error(data):
            logger.error(f"SocketIO error: {data}")

    def _handle_tick(self, data: dict):
        """
        Handle incoming tick from Flask.

        Detects bet placements and mirrors to browser if enabled.
        """
        tick = data.get("tick", {})
        session = data.get("session", {})

        tick_count = tick.get("tickCount", 0)
        price = tick.get("price", 0)

        # Notify UI
        if self._on_tick_callback:
            self._on_tick_callback(tick_count, price)

        # Check for new bets
        current_bets = set(session.get("bets_placed_this_game", []))
        new_bets = current_bets - self._last_bets_placed

        if new_bets:
            # New bet(s) were placed in Flask
            active_bets = session.get("active_bets", [])

            for bet_num in new_bets:
                # Find the bet details
                bet_info = None
                for bet in active_bets:
                    if bet.get("bet_num") == bet_num:
                        bet_info = bet
                        break

                if bet_info:
                    bet_size = bet_info.get("size", 0.001)
                    logger.info(
                        f"[MIRROR] Detected bet {bet_num}: {bet_size} SOL at tick {tick_count}"
                    )

                    # Notify UI
                    if self._on_bet_callback:
                        self._on_bet_callback(bet_num, bet_size, tick_count)

                    # Execute if enabled
                    if self._enabled and self.execution_bridge:
                        self._execute_bet(bet_size, bet_num, len(current_bets))

        # Update tracking state
        self._last_bets_placed = current_bets
        self._last_active_bets = session.get("active_bets", [])

    def _execute_bet(self, bet_size: float, bet_num: int, total_bets: int):
        """Execute a bet via the browser."""
        if not self.execution_bridge:
            logger.warning("No execution bridge - cannot execute")
            return

        logger.warning(f"[EXECUTE] Placing real bet {bet_num}: {bet_size} SOL")

        # Stage next bet for front-running if not last bet
        if bet_num < 4:  # Assuming max 4 bets
            # We don't know next bet size here, but the session has bet_sizes
            # For now, skip front-running - can be enhanced later
            pass

        # Execute via async bridge
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.execution_bridge.execute_sidebet(Decimal(str(bet_size))))
            loop.close()
        except Exception as e:
            logger.error(f"Execution failed: {e}")

    def connect(self) -> bool:
        """Connect to Flask SocketIO server."""
        try:
            self.sio.connect(self.flask_url)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Flask: {e}")
            return False

    def disconnect(self):
        """Disconnect from Flask SocketIO."""
        if self.sio.connected:
            self.sio.disconnect()

    def join_session(self, session_id: str, strategy: dict):
        """
        Join a live session.

        This should match the session started in Flask dashboard.
        """
        self._session_id = session_id
        self._last_bets_placed = set()

        self.sio.emit(
            "join_live",
            {
                "session_id": session_id,
                "strategy": strategy,
            },
        )
        logger.info(f"Requested to join session: {session_id}")

    def leave_session(self):
        """Leave the current session."""
        if self._session_id:
            self.sio.emit("leave_live", {"session_id": self._session_id})
            self._session_id = None

    def enable_execution(self):
        """Enable real execution mirroring."""
        self._enabled = True
        if self.execution_bridge:
            self.execution_bridge.enable()
        logger.warning("EXECUTION ENABLED - Will mirror bets to browser!")

    def disable_execution(self):
        """Disable real execution mirroring."""
        self._enabled = False
        if self.execution_bridge:
            self.execution_bridge.disable()
        logger.info("Execution disabled")

    @property
    def is_connected(self) -> bool:
        return self.sio.connected

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_tick_callback(self, callback: Callable[[int, float], None]):
        """Set callback for tick updates: callback(tick_count, price)"""
        self._on_tick_callback = callback

    def set_bet_callback(self, callback: Callable[[int, float, int], None]):
        """Set callback for bet detection: callback(bet_num, size, tick)"""
        self._on_bet_callback = callback
