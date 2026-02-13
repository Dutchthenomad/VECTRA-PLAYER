# 12 - Live Trading Mode (Backtest Tab)

## Purpose

Paper trade against live rugs.fun game data:
1. Real-time WebSocket feed integration
2. Virtual position tracking
3. Live strategy execution
4. Performance monitoring

## Dependencies

```python
# Internal services
from recording_ui.services.live_backtest_service import (
    LiveBacktestService,
    LiveSession,
    get_live_backtest_service,
)
from flask_socketio import SocketIO, emit, join_room, leave_room
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Live Trading Mode                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     rugs.fun WebSocket Feed                          │    │
│  │                   wss://rugs.fun/socket.io/...                      │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                  │                                           │
│                                  ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    LiveBacktestService                               │    │
│  │                                                                      │    │
│  │  gameStateUpdate ──────▶ _on_game_state_update()                    │    │
│  │                              │                                       │    │
│  │                              ├── Update tick/price                   │    │
│  │                              ├── Check bet windows                   │    │
│  │                              ├── Execute strategy                    │    │
│  │                              └── Broadcast to sessions               │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                  │                                           │
│           ┌──────────────────────┼──────────────────────┐                   │
│           │                      │                      │                    │
│           ▼                      ▼                      ▼                    │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐          │
│  │ Session A      │     │ Session B      │     │ Session C      │          │
│  │ (Paper Trade)  │     │ (Paper Trade)  │     │ (Observer)     │          │
│  │                │     │                │     │                │          │
│  │ Strategy: X    │     │ Strategy: Y    │     │ No Strategy    │          │
│  │ Balance: 0.15  │     │ Balance: 0.08  │     │                │          │
│  └────────────────┘     └────────────────┘     └────────────────┘          │
│           │                      │                      │                    │
│           │         SocketIO     │                      │                    │
│           ▼         Rooms        ▼                      ▼                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Frontend Clients                                   │  │
│  │    Browser A          Browser B          Browser C                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Live Session State

```python
# src/recording_ui/services/live_backtest_service.py

from dataclasses import dataclass, field
from typing import Any

@dataclass
class LiveSession:
    """State for a live paper trading session"""
    session_id: str
    strategy: dict
    is_active: bool = True

    # Current game
    current_game_id: str = ""
    current_tick: int = 0
    current_price: float = 1.0

    # Virtual portfolio
    wallet: float = 0.1
    peak_wallet: float = 0.1

    # Session statistics
    games_played: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_bets_placed: int = 0

    # Current game bet tracking
    bets_this_game: list[dict] = field(default_factory=list)
    active_bet: dict | None = None  # Currently active bet window

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "strategy": self.strategy,
            "is_active": self.is_active,
            "current_game_id": self.current_game_id[:8] if self.current_game_id else "",
            "current_tick": self.current_tick,
            "current_price": self.current_price,
            "wallet": self.wallet,
            "peak_wallet": self.peak_wallet,
            "games_played": self.games_played,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "total_bets_placed": self.total_bets_placed,
            "win_rate": self.total_wins / max(self.total_bets_placed, 1),
            "bets_this_game": self.bets_this_game,
            "active_bet": self.active_bet,
        }
```

### 2. LiveBacktestService

```python
class LiveBacktestService:
    """Manages live paper trading sessions"""

    def __init__(self, socketio: SocketIO):
        self._socketio = socketio
        self.sessions: dict[str, LiveSession] = {}
        self._ws_feed = None
        self._is_connected = False
        self._last_game_id = None
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._is_connected

    def start_session(self, session_id: str, strategy: dict) -> LiveSession:
        """
        Start a new live paper trading session.

        Args:
            session_id: Unique session identifier
            strategy: Strategy configuration

        Returns:
            LiveSession instance
        """
        session = LiveSession(
            session_id=session_id,
            strategy=strategy,
            wallet=strategy.get("initial_balance", 0.1),
        )
        session.peak_wallet = session.wallet

        with self._lock:
            self.sessions[session_id] = session

        logger.info(f"Live session started: {session_id}")
        return session

    def stop_session(self, session_id: str):
        """Stop a live session"""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].is_active = False
                del self.sessions[session_id]
        logger.info(f"Live session stopped: {session_id}")

    def get_session(self, session_id: str) -> LiveSession | None:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def ensure_ws_connected(self):
        """Ensure WebSocket connection to rugs.fun"""
        if self._is_connected:
            return

        from sources.websocket_feed import WebSocketFeed

        self._ws_feed = WebSocketFeed()
        self._ws_feed.on("signal", self._on_game_state_update)
        self._ws_feed.on("connected", lambda _: self._on_ws_connected())
        self._ws_feed.on("disconnected", lambda _: self._on_ws_disconnected())

        # Start connection in background thread
        threading.Thread(
            target=self._ws_feed.connect,
            daemon=True,
            name="LiveBacktest-WS"
        ).start()

    def _on_ws_connected(self):
        """Handle WebSocket connection"""
        self._is_connected = True
        logger.info("Live backtest WebSocket connected")

    def _on_ws_disconnected(self):
        """Handle WebSocket disconnection"""
        self._is_connected = False
        logger.warning("Live backtest WebSocket disconnected")
```

### 3. Game State Update Handler

```python
def _on_game_state_update(self, signal):
    """
    Handle gameStateUpdate from WebSocket.

    Called for every tick of the live game.
    """
    game_id = signal.game_id
    tick = signal.tick_count
    price = signal.price
    rugged = signal.rugged

    # Detect new game
    if game_id != self._last_game_id:
        self._on_new_game(game_id)
        self._last_game_id = game_id

    # Update all sessions
    with self._lock:
        for session_id, session in self.sessions.items():
            if not session.is_active:
                continue

            # Update game state
            session.current_game_id = game_id
            session.current_tick = tick
            session.current_price = price

            # Execute strategy
            self._execute_strategy(session, tick, price, rugged)

            # Broadcast to client
            self._broadcast_tick(session_id, session)

    # Handle rug event
    if rugged:
        self._on_game_rugged(game_id, tick)

def _execute_strategy(self, session: LiveSession, tick: int,
                      price: float, rugged: bool):
    """Execute strategy logic for a session"""
    strategy = session.strategy
    entry_tick = strategy.get("entry_tick", 200)
    bet_sizes = strategy.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])
    num_bets = strategy.get("num_bets", len(bet_sizes))

    # Check if we should place a bet
    for bet_num in range(1, num_bets + 1):
        bet_start = entry_tick + (bet_num - 1) * 45

        # Check if this is the tick to place bet
        if tick == bet_start:
            # Check if we already placed this bet
            if any(b["bet_number"] == bet_num for b in session.bets_this_game):
                continue

            bet_size = bet_sizes[bet_num - 1] if bet_num <= len(bet_sizes) else bet_sizes[-1]
            bet_size = min(bet_size, session.wallet)  # Can't bet more than have

            if bet_size > 0:
                self._place_virtual_bet(session, bet_num, bet_start, bet_size)

    # Check active bet outcomes
    if session.active_bet:
        bet = session.active_bet
        if rugged and bet["start_tick"] <= tick < bet["end_tick"]:
            # WIN
            self._resolve_bet(session, bet, True)
        elif tick >= bet["end_tick"]:
            # LOSS (window ended)
            self._resolve_bet(session, bet, False)

def _place_virtual_bet(self, session: LiveSession, bet_num: int,
                       start_tick: int, bet_size: float):
    """Place a virtual sidebet"""
    bet = {
        "bet_number": bet_num,
        "start_tick": start_tick,
        "end_tick": start_tick + 40,
        "bet_size": bet_size,
        "status": "active",
    }

    session.bets_this_game.append(bet)
    session.active_bet = bet
    session.total_bets_placed += 1

    logger.debug(f"Session {session.session_id}: Placed bet #{bet_num} "
                 f"at tick {start_tick}, size {bet_size:.4f}")

def _resolve_bet(self, session: LiveSession, bet: dict, won: bool):
    """Resolve a virtual bet"""
    if won:
        payout = bet["bet_size"] * 5  # 5:1 payout
        session.wallet += payout - bet["bet_size"]  # Net profit
        session.total_wins += 1
        bet["status"] = "won"
        bet["payout"] = payout
        logger.info(f"Session {session.session_id}: WON bet #{bet['bet_number']}, "
                    f"payout {payout:.4f}")
    else:
        session.wallet -= bet["bet_size"]
        session.total_losses += 1
        bet["status"] = "lost"
        logger.info(f"Session {session.session_id}: LOST bet #{bet['bet_number']}")

    # Update peak
    if session.wallet > session.peak_wallet:
        session.peak_wallet = session.wallet

    session.active_bet = None
```

### 4. SocketIO Broadcasting

```python
def _broadcast_tick(self, session_id: str, session: LiveSession):
    """Broadcast tick update to session room"""
    self._socketio.emit(
        "live_tick",
        {
            "tick": session.current_tick,
            "price": session.current_price,
            "game_id": session.current_game_id[:8] if session.current_game_id else "",
            "session": session.to_dict(),
        },
        room=session_id
    )

def _on_new_game(self, game_id: str):
    """Handle start of new game"""
    with self._lock:
        for session_id, session in self.sessions.items():
            # Reset game-specific state
            session.bets_this_game = []
            session.active_bet = None
            session.games_played += 1

            # Broadcast game start
            self._socketio.emit(
                "live_game_start",
                {
                    "game_id": game_id[:8],
                    "session": session.to_dict(),
                },
                room=session_id
            )

def _on_game_rugged(self, game_id: str, final_tick: int):
    """Handle game rug event"""
    with self._lock:
        for session_id, session in self.sessions.items():
            self._socketio.emit(
                "live_game_end",
                {
                    "game_id": game_id[:8],
                    "final_tick": final_tick,
                    "session": session.to_dict(),
                },
                room=session_id
            )
```

### 5. SocketIO Event Handlers

```python
# src/recording_ui/app.py

@socketio.on("join_live")
def handle_join_live(data):
    """Frontend joins live feed with strategy"""
    session_id = data.get("session_id")
    strategy = data.get("strategy", {})

    if not session_id:
        emit("error", {"message": "session_id required"})
        return

    # Join room
    join_room(session_id)

    # Start session
    session = live_backtest_service.start_session(session_id, strategy)

    # Ensure WebSocket connected
    live_backtest_service.ensure_ws_connected()

    # Send initial state
    emit("live_joined", {
        "session_id": session_id,
        "session": session.to_dict(),
    })

    logger.info(f"Client joined live session {session_id}")

@socketio.on("leave_live")
def handle_leave_live(data):
    """Frontend leaves live feed"""
    session_id = data.get("session_id")
    if session_id:
        leave_room(session_id)
        live_backtest_service.stop_session(session_id)
        logger.info(f"Client left live session {session_id}")
```

## Frontend Integration

### SocketIO Client

```javascript
// static/js/backtest.js

class LiveTradingController {
    constructor() {
        this.socket = io();
        this.sessionId = null;
        this.session = null;

        // Event handlers
        this.socket.on('live_tick', this.onLiveTick.bind(this));
        this.socket.on('live_game_start', this.onGameStart.bind(this));
        this.socket.on('live_game_end', this.onGameEnd.bind(this));
        this.socket.on('live_joined', this.onJoined.bind(this));
        this.socket.on('error', this.onError.bind(this));
    }

    joinLive(strategy) {
        this.sessionId = 'live-' + Date.now();
        this.socket.emit('join_live', {
            session_id: this.sessionId,
            strategy: strategy
        });
    }

    leaveLive() {
        if (this.sessionId) {
            this.socket.emit('leave_live', {
                session_id: this.sessionId
            });
            this.sessionId = null;
        }
    }

    onJoined(data) {
        this.session = data.session;
        this.updateDisplay();
        showNotification('Connected to live feed');
    }

    onLiveTick(data) {
        this.session = data.session;
        this.updateTickDisplay(data.tick, data.price);
        this.updateChart();
        this.updateBetStatus();
    }

    onGameStart(data) {
        console.log('New game started:', data.game_id);
        this.resetChartForNewGame();
        showNotification(`Game ${data.game_id} started`);
    }

    onGameEnd(data) {
        console.log('Game ended:', data.game_id, 'at tick', data.final_tick);
        this.showGameEndOverlay(data);
    }

    updateDisplay() {
        document.getElementById('wallet').textContent =
            this.session.wallet.toFixed(4) + ' SOL';
        document.getElementById('wins').textContent = this.session.total_wins;
        document.getElementById('losses').textContent = this.session.total_losses;
        document.getElementById('win-rate').textContent =
            (this.session.win_rate * 100).toFixed(1) + '%';
    }
}
```

## API Endpoint

```python
@app.route("/api/live/status")
def api_live_status():
    """Get WebSocket connection status"""
    service = get_live_backtest_service(socketio)
    return jsonify({
        "connected": service.is_connected,
        "active_sessions": len(service.sessions),
        "session_ids": list(service.sessions.keys()),
    })

@app.route("/api/live/sessions")
def get_live_sessions():
    """Get list of active live sessions"""
    sessions = []
    for session_id, session in live_backtest_service.sessions.items():
        if session.is_active:
            sessions.append({
                "session_id": session_id,
                "strategy_name": session.strategy.get("name", "unknown"),
                "games_played": session.games_played,
                "wallet": session.wallet,
            })
    return jsonify({"sessions": sessions, "count": len(sessions)})
```

## Gotchas

1. **WebSocket Reconnection**: Direct WebSocket gets public events only (no authenticated player data).

2. **Bet Timing**: Place bet exactly at start_tick to match backtested behavior.

3. **Rug Detection**: Check `rugged` flag, not just tick >= duration (duration unknown until rug).

4. **Thread Safety**: Lock when iterating/modifying sessions dict.

5. **Room-based Emit**: Use SocketIO rooms for session-specific broadcasts.

6. **Balance Tracking**: Virtual balance only. No real trading.

7. **New Game Reset**: Clear bets_this_game on new game detection.
