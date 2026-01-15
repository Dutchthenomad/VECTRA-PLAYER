"""
Live Backtest Service - Paper trading with real-time WebSocket feed.

Connects to rugs.fun WebSocket and runs loaded strategy against live game data.
This is the vetting stage before real money deployment - observe bot decisions
on live data without actually placing bets.

Usage:
    # In app.py with Flask-SocketIO
    from flask_socketio import SocketIO
    from recording_ui.services.live_backtest_service import get_live_backtest_service

    socketio = SocketIO(app)
    live_service = get_live_backtest_service(socketio)
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.execution_bridge import BotExecutionBridge

logger = logging.getLogger(__name__)

# Constants (same as backtest_service.py)
SIDEBET_WINDOW = 40
SIDEBET_COOLDOWN = 5
SIDEBET_PAYOUT = 5  # 5:1


@dataclass
class LiveActiveBet:
    """A simulated bet that has been placed in live mode."""

    bet_num: int  # 1-4
    tick_placed: int
    size: float
    entry_price: float
    window_end: int  # tick_placed + 40
    game_id: str
    resolved: bool = False
    won: bool = False


@dataclass
class LiveSession:
    """State of a live paper trading session."""

    session_id: str
    strategy: dict

    # Wallet
    initial_balance: float = 0.1
    wallet: float = 0.1
    peak_balance: float = 0.1

    # Current game tracking
    current_game_id: str | None = None
    bets_placed_this_game: list[int] = field(default_factory=list)

    # Active bets
    active_bets: list[LiveActiveBet] = field(default_factory=list)

    # Stats
    wins: int = 0
    losses: int = 0
    games_played: int = 0
    total_wagered: float = 0.0
    max_drawdown: float = 0.0

    # Equity curve (last 100 points)
    equity_curve: list[float] = field(default_factory=list)

    # Live state
    is_active: bool = True
    last_tick: dict | None = None
    connection_status: str = "disconnected"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for frontend."""
        return {
            "session_id": self.session_id,
            "strategy_name": self.strategy.get("name", "unnamed"),
            "mode": "live",
            # Game state (from last tick)
            "game": {
                "game_id": self.current_game_id,
                "current_tick": self.last_tick.get("tickCount", 0) if self.last_tick else 0,
                "current_price": float(self.last_tick.get("price", 1.0)) if self.last_tick else 1.0,
                "phase": self.last_tick.get("phase", "unknown") if self.last_tick else "waiting",
                "duration": None,  # Unknown in live mode
            }
            if self.last_tick
            else None,
            # Wallet
            "wallet": round(self.wallet, 6),
            "initial_balance": self.initial_balance,
            "pnl": round(self.wallet - self.initial_balance, 6),
            "pnl_pct": round((self.wallet - self.initial_balance) / self.initial_balance * 100, 2)
            if self.initial_balance > 0
            else 0,
            # Active bets
            "active_bets": [
                {
                    "bet_num": b.bet_num,
                    "tick_placed": b.tick_placed,
                    "entry_tick": b.tick_placed,
                    "entry_price": b.entry_price,
                    "amount": b.size,
                    "size": b.size,
                    "window_end": b.window_end,
                    "game_id": b.game_id,
                    "resolved": b.resolved,
                    "won": b.won,
                }
                for b in self.active_bets
                if not b.resolved
            ],
            # Stats
            "cumulative_stats": {
                "wins": self.wins,
                "losses": self.losses,
                "total_games": self.games_played,
                "games_played": self.games_played,
                "win_rate": round(self.wins / self.games_played * 100, 1)
                if self.games_played > 0
                else 0,
                "total_wagered": round(self.total_wagered, 6),
                "max_drawdown": round(self.max_drawdown * 100, 2),
            },
            "equity_curve": [round(e, 6) for e in self.equity_curve[-100:]],
            # Live status
            "is_active": self.is_active,
            "connection_status": self.connection_status,
            "finished": False,  # Live mode never finishes
            "paused": not self.is_active,
        }


class LiveBacktestService:
    """Service for running strategy against live WebSocket feed."""

    def __init__(self, socketio=None):
        """
        Initialize the live backtest service.

        Args:
            socketio: Flask-SocketIO instance for emitting updates to frontend
        """
        self.socketio = socketio
        self.sessions: dict[str, LiveSession] = {}
        self.ws_feed = None
        self._ws_thread: threading.Thread | None = None
        self._connected = False
        self._lock = threading.Lock()

        # Real execution support (Phase 2)
        self.execution_bridge: BotExecutionBridge | None = None
        self.real_execution_enabled = False
        self._async_loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_connected(self) -> bool:
        """Public property for WebSocket connection status."""
        return self._connected

    def start_session(self, session_id: str, strategy: dict) -> LiveSession:
        """
        Start a new paper trading session.

        Args:
            session_id: Unique session identifier
            strategy: Strategy configuration (same format as backtest)

        Returns:
            The created LiveSession
        """
        initial_balance = strategy.get("initial_balance", 0.1)

        session = LiveSession(
            session_id=session_id,
            strategy=strategy,
            initial_balance=initial_balance,
            wallet=initial_balance,
            peak_balance=initial_balance,
            equity_curve=[initial_balance],
        )

        with self._lock:
            self.sessions[session_id] = session

        logger.info(
            f"Started live session {session_id} with strategy '{strategy.get('name', 'unnamed')}'"
        )
        return session

    def stop_session(self, session_id: str) -> None:
        """Stop and remove a session."""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].is_active = False
                del self.sessions[session_id]
                logger.info(f"Stopped live session {session_id}")

    def get_session(self, session_id: str) -> LiveSession | None:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    # ========================================================================
    # REAL EXECUTION (Phase 2)
    # ========================================================================

    def set_execution_bridge(self, bridge: "BotExecutionBridge") -> None:
        """
        Wire execution bridge for real trading.

        Args:
            bridge: BotExecutionBridge instance
        """
        self.execution_bridge = bridge
        logger.info("Execution bridge wired to LiveBacktestService")

    def enable_real_execution(self) -> None:
        """
        Enable real money execution.

        WARNING: This enables real money trading!
        Bot decisions will be executed via browser buttons.
        """
        if self.execution_bridge is None:
            logger.error("Cannot enable real execution: no execution bridge set")
            return

        self.execution_bridge.enable()
        self.real_execution_enabled = True

        # Create async event loop for execution
        if self._async_loop is None or self._async_loop.is_closed():
            self._async_loop = asyncio.new_event_loop()

        logger.warning("REAL EXECUTION ENABLED - Bot will place real bets!")

    def disable_real_execution(self) -> None:
        """Disable real money execution."""
        if self.execution_bridge:
            self.execution_bridge.disable()
        self.real_execution_enabled = False
        logger.info("Real execution disabled")

    def _execute_in_async_loop(self, coro) -> None:
        """
        Execute an async coroutine from sync context.

        Runs the coroutine in a background thread with its own event loop.
        """

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    def ensure_ws_connected(self) -> bool:
        """
        Ensure WebSocket is connected to rugs.fun.
        Starts connection in background thread if not already connected.

        Returns:
            True if connected or connecting, False if failed
        """
        if self._connected and self.ws_feed:
            return True

        if self._ws_thread and self._ws_thread.is_alive():
            return True  # Already connecting

        try:
            self._ws_thread = threading.Thread(
                target=self._connect_websocket, daemon=True, name="LiveBacktest-WS"
            )
            self._ws_thread.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start WebSocket thread: {e}")
            return False

    def _connect_websocket(self) -> None:
        """Connect to rugs.fun WebSocket (runs in background thread)."""
        try:
            # Import here to avoid circular imports
            from sources.websocket_feed import WebSocketFeed

            self.ws_feed = WebSocketFeed(log_level="INFO")

            # Register event handlers
            self.ws_feed.on("signal", self._on_game_tick)
            self.ws_feed.on("gameComplete", self._on_game_complete)
            self.ws_feed.on("connected", self._on_connected)
            self.ws_feed.on("disconnected", self._on_disconnected)

            # Update session status
            for session in self.sessions.values():
                session.connection_status = "connecting"

            # Connect (blocking)
            self.ws_feed.connect()
            self._connected = True

            # Wait for events
            self.ws_feed.wait()

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._connected = False
            for session in self.sessions.values():
                session.connection_status = f"error: {str(e)[:50]}"

    def _on_connected(self, data: dict) -> None:
        """Handle WebSocket connected event."""
        self._connected = True
        for session in self.sessions.values():
            session.connection_status = "connected"
        logger.info("Live backtest: Connected to rugs.fun")

    def _on_disconnected(self, data: dict) -> None:
        """Handle WebSocket disconnected event."""
        self._connected = False
        for session in self.sessions.values():
            session.connection_status = "disconnected"
        logger.warning("Live backtest: Disconnected from rugs.fun")

    def _on_game_tick(self, signal) -> None:
        """
        Process each game tick from WebSocket.
        Runs strategy logic and emits updates to frontend.

        Args:
            signal: GameSignal from WebSocketFeed
        """
        # Convert signal to dict for processing
        tick_data = {
            "gameId": signal.gameId,
            "tickCount": signal.tickCount,
            "price": float(signal.price) if isinstance(signal.price, Decimal) else signal.price,
            "active": signal.active,
            "rugged": signal.rugged,
            "phase": signal.phase,
            "timestamp": signal.timestamp,
        }

        # Process for each active session
        with self._lock:
            sessions_to_process = list(self.sessions.items())

        for session_id, session in sessions_to_process:
            if not session.is_active:
                continue

            try:
                # Update last tick
                session.last_tick = tick_data

                # Check for new game
                if session.current_game_id != tick_data["gameId"]:
                    self._on_new_game(session, tick_data)

                # Run bet placement logic
                self._check_bet_placement(session, tick_data)

                # Check for bet resolution (rug detection)
                if tick_data.get("rugged"):
                    self._check_bet_resolution(session, tick_data)

                # Emit update to frontend via SocketIO
                if self.socketio:
                    self.socketio.emit(
                        "live_tick",
                        {
                            "tick": tick_data,
                            "session": session.to_dict(),
                        },
                        room=session_id,
                    )

            except Exception as e:
                logger.error(f"Error processing tick for session {session_id}: {e}")

    def _on_new_game(self, session: LiveSession, tick_data: dict) -> None:
        """Handle transition to a new game."""
        old_game = session.current_game_id
        session.current_game_id = tick_data["gameId"]
        session.bets_placed_this_game = []

        if old_game:
            # Count as a played game (even if no bets)
            session.games_played += 1
            # Update equity curve
            session.equity_curve.append(session.wallet)

        logger.debug(f"Session {session.session_id}: New game {tick_data['gameId']}")

    def _on_game_complete(self, data: dict) -> None:
        """Handle game completion event."""
        # This is called when rug is detected - additional handling if needed
        pass

    def _check_bet_placement(self, session: LiveSession, tick_data: dict) -> None:
        """
        Check if we should place a simulated bet this tick.
        Follows same logic as backtest_service.py.
        """
        if not tick_data.get("active"):
            return  # Only bet during active game

        tick_count = tick_data["tickCount"]
        strategy = session.strategy.get("params", session.strategy)
        entry_tick = strategy.get("entry_tick", 200)
        num_bets = strategy.get("num_bets", 4)

        # Log progress every 50 ticks and near entry tick
        if tick_count % 50 == 0 or (entry_tick - 5 <= tick_count <= entry_tick + 5):
            logger.info(
                f"Tick {tick_count}: price={tick_data['price']:.2f}x, entry_tick={entry_tick}, bets_placed={session.bets_placed_this_game}"
            )

        # Check each bet slot
        for bet_num in range(1, num_bets + 1):
            if bet_num in session.bets_placed_this_game:
                continue

            # Calculate when this bet should be placed
            bet_start = entry_tick + (bet_num - 1) * (SIDEBET_WINDOW + SIDEBET_COOLDOWN)

            if tick_count == bet_start:
                # Place the bet
                bet_size = self._calculate_bet_size(session, strategy, bet_num)
                bet_sizes = strategy.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])

                if bet_size > session.wallet:
                    logger.debug(
                        f"Session {session.session_id}: Can't afford bet {bet_num} ({bet_size:.4f} > {session.wallet:.4f})"
                    )
                    continue

                # Deduct from wallet (paper trading always tracks)
                session.wallet -= bet_size
                session.total_wagered += bet_size

                # Record the bet
                session.active_bets.append(
                    LiveActiveBet(
                        bet_num=bet_num,
                        tick_placed=tick_count,
                        size=bet_size,
                        entry_price=tick_data["price"],
                        window_end=tick_count + SIDEBET_WINDOW,
                        game_id=tick_data["gameId"],
                    )
                )
                session.bets_placed_this_game.append(bet_num)

                logger.info(
                    f"Session {session.session_id}: Placed bet {bet_num} "
                    f"({bet_size:.4f} SOL) at tick {tick_count}, price {tick_data['price']:.2f}x"
                )

                # REAL EXECUTION: Execute via browser if enabled
                if self.real_execution_enabled and self.execution_bridge:
                    # Stage NEXT bet amount for front-running
                    if bet_num < num_bets:
                        next_size = self._calculate_bet_size(session, strategy, bet_num + 1)
                        self.execution_bridge.stage_next_amount(Decimal(str(next_size)))
                        logger.info(f"Staged next bet: {next_size:.4f} SOL for front-running")

                    # Execute current bet via async bridge
                    self._execute_in_async_loop(
                        self.execution_bridge.execute_sidebet(Decimal(str(bet_size)))
                    )
                    logger.info(f"Real execution triggered for bet {bet_num}")

    def _calculate_bet_size(self, session: LiveSession, strategy: dict, bet_num: int) -> float:
        """
        Calculate bet size based on strategy (same logic as backtest_service).

        Args:
            session: Current session
            strategy: Strategy params
            bet_num: Which bet (1-4)

        Returns:
            Bet size in SOL
        """
        bet_sizes = strategy.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])

        if bet_num <= len(bet_sizes):
            base_size = bet_sizes[bet_num - 1]
        else:
            base_size = 0.001

        # Kelly sizing
        if strategy.get("use_kelly_sizing", False):
            kelly_fraction = strategy.get("kelly_fraction", 0.25)
            # Simplified Kelly - use ~60% win rate assumption
            kelly_full = 0.60 - (1 - 0.60) / SIDEBET_PAYOUT
            kelly_adjusted = kelly_full * kelly_fraction
            base_size = max(0.0001, session.wallet * kelly_adjusted / 4)

        # Dynamic sizing
        if strategy.get("use_dynamic_sizing", False):
            multiplier = strategy.get("high_confidence_multiplier", 2.0)
            base_size *= multiplier

        # Reduce on drawdown
        if strategy.get("reduce_on_drawdown", False):
            if session.peak_balance > 0:
                current_dd = (session.peak_balance - session.wallet) / session.peak_balance
                if current_dd > 0.05:
                    reduction = min(0.9, current_dd)
                    base_size *= 1 - reduction

        # Round to 3 decimal places (rugs.fun UI precision)
        return round(max(0.001, base_size), 3)

    def _check_bet_resolution(self, session: LiveSession, tick_data: dict) -> None:
        """
        Check if any active bets should be resolved.
        Called when rugged=true is detected.
        """
        if not tick_data.get("rugged"):
            return

        rug_tick = tick_data["tickCount"]
        game_id = tick_data["gameId"]

        any_resolved = False
        for bet in session.active_bets:
            if bet.resolved:
                continue
            if bet.game_id != game_id:
                continue  # Bet from different game

            bet.resolved = True
            any_resolved = True

            # Win if rug happened within window
            if bet.tick_placed <= rug_tick <= bet.window_end:
                bet.won = True
                payout = bet.size * SIDEBET_PAYOUT
                session.wallet += payout
                session.wins += 1
                logger.info(
                    f"Session {session.session_id}: Bet {bet.bet_num} WON! "
                    f"Payout {payout:.4f} SOL (rug at tick {rug_tick}, window was {bet.tick_placed}-{bet.window_end})"
                )
            else:
                bet.won = False
                session.losses += 1
                logger.info(
                    f"Session {session.session_id}: Bet {bet.bet_num} LOST "
                    f"(rug at tick {rug_tick}, window was {bet.tick_placed}-{bet.window_end})"
                )

        if any_resolved:
            # Update peak and drawdown
            if session.wallet > session.peak_balance:
                session.peak_balance = session.wallet

            if session.peak_balance > 0:
                current_dd = (session.peak_balance - session.wallet) / session.peak_balance
                session.max_drawdown = max(session.max_drawdown, current_dd)

            # Clean up resolved bets
            session.active_bets = [b for b in session.active_bets if not b.resolved]

    def disconnect_ws(self) -> None:
        """Disconnect from WebSocket."""
        if self.ws_feed:
            try:
                self.ws_feed.disconnect()
            except Exception:
                pass
        self._connected = False


# Singleton instance
_service: LiveBacktestService | None = None


def get_live_backtest_service(socketio=None) -> LiveBacktestService:
    """
    Get the singleton live backtest service instance.

    Args:
        socketio: Flask-SocketIO instance (required on first call)

    Returns:
        LiveBacktestService instance
    """
    global _service
    if _service is None:
        _service = LiveBacktestService(socketio)
    elif socketio is not None and _service.socketio is None:
        _service.socketio = socketio
    return _service
