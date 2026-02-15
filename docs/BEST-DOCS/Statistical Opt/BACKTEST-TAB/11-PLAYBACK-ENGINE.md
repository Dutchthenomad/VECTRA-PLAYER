# 11 - Playback Engine (Backtest Tab)

## Purpose

Replay historical games tick-by-tick for strategy visualization:
1. Time-controlled playback (pause, speed, step)
2. Visual bet window overlay
3. Outcome tracking per game
4. Strategy performance metrics

## Dependencies

```python
# Internal services
from recording_ui.services.backtest_service import (
    BacktestService,
    PlaybackState,
    get_backtest_service,
)
from recording_ui.services.explorer_data import load_games_df
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Backtest Playback Engine                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │    Strategy     │                                                         │
│  │  Configuration  │                                                         │
│  │  - entry_tick   │                                                         │
│  │  - num_bets     │                                                         │
│  │  - bet_sizes    │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                   │
│           ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                       Playback State Machine                            │ │
│  │                                                                         │ │
│  │  ┌─────────┐    tick()    ┌─────────┐   tick()   ┌─────────┐         │ │
│  │  │ PAUSED  │◀────────────▶│ PLAYING │───────────▶│COMPLETED│         │ │
│  │  └─────────┘              └─────────┘            └─────────┘         │ │
│  │       │                        │                                      │ │
│  │       │     next_game()       │                                      │ │
│  │       └───────────────────────┘                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│           │                                                                   │
│           ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Playback State                                   │ │
│  │  - current_tick: int                                                   │ │
│  │  - current_price: float                                                │ │
│  │  - current_game_idx: int                                               │ │
│  │  - prices: list[float]                                                 │ │
│  │  - bet_windows: list[BetWindow]                                        │ │
│  │  - session_stats: {wins, losses, balance}                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Playback State

```python
# src/recording_ui/services/backtest_service.py

from dataclasses import dataclass, field
from enum import Enum

class PlaybackStatus(Enum):
    PAUSED = "paused"
    PLAYING = "playing"
    COMPLETED = "completed"

@dataclass
class BetWindow:
    """Represents a sidebet window during playback"""
    bet_number: int
    start_tick: int
    end_tick: int
    bet_size: float
    outcome: str = "pending"  # pending, win, loss, skipped
    payout: float = 0.0

@dataclass
class PlaybackState:
    """Current state of backtest playback"""
    session_id: str
    status: PlaybackStatus = PlaybackStatus.PAUSED

    # Game state
    current_game_idx: int = 0
    current_tick: int = 0
    current_price: float = 1.0
    prices: list[float] = field(default_factory=list)
    game_duration: int = 0
    game_id: str = ""

    # Bet windows for current game
    bet_windows: list[BetWindow] = field(default_factory=list)

    # Session statistics
    games_played: int = 0
    total_wins: int = 0
    total_losses: int = 0
    current_balance: float = 0.1
    peak_balance: float = 0.1

    # Playback settings
    speed_multiplier: float = 1.0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_game_idx": self.current_game_idx,
            "current_tick": self.current_tick,
            "current_price": self.current_price,
            "prices": self.prices,
            "game_duration": self.game_duration,
            "game_id": self.game_id,
            "bet_windows": [
                {
                    "bet_number": bw.bet_number,
                    "start_tick": bw.start_tick,
                    "end_tick": bw.end_tick,
                    "bet_size": bw.bet_size,
                    "outcome": bw.outcome,
                    "payout": bw.payout,
                }
                for bw in self.bet_windows
            ],
            "games_played": self.games_played,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "current_balance": self.current_balance,
            "speed_multiplier": self.speed_multiplier,
        }
```

### 2. Backtest Service

```python
class BacktestService:
    """Manages backtest playback sessions"""

    def __init__(self):
        self._sessions: dict[str, PlaybackState] = {}
        self._games_df: pd.DataFrame | None = None
        self._validation_games: list[dict] | None = None

    def start_playback(self, strategy: dict) -> str:
        """
        Start a new playback session.

        Args:
            strategy: Strategy configuration with entry_tick, bet_sizes, etc.

        Returns:
            Session ID
        """
        import uuid
        session_id = str(uuid.uuid4())[:8]

        # Load games if not already loaded
        if self._games_df is None:
            self._games_df = load_games_df()
            self._validation_games = self._prepare_validation_games()

        # Create session state
        state = PlaybackState(
            session_id=session_id,
            current_balance=strategy.get("initial_balance", 0.1),
        )
        state.peak_balance = state.current_balance

        # Store strategy config
        self._strategies[session_id] = strategy

        # Load first game
        self._load_game(state, 0, strategy)

        self._sessions[session_id] = state
        return session_id

    def _load_game(self, state: PlaybackState, game_idx: int, strategy: dict):
        """Load a game into playback state"""
        game = self._validation_games[game_idx]

        state.current_game_idx = game_idx
        state.current_tick = 0
        state.game_id = game["game_id"]
        state.prices = game["prices"]
        state.game_duration = game["duration"]
        state.current_price = state.prices[0] if state.prices else 1.0

        # Create bet windows
        entry_tick = strategy.get("entry_tick", 200)
        bet_sizes = strategy.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])
        num_bets = strategy.get("num_bets", len(bet_sizes))

        state.bet_windows = []
        for bet_num in range(1, num_bets + 1):
            start_tick = entry_tick + (bet_num - 1) * 45
            end_tick = start_tick + 40
            bet_size = bet_sizes[bet_num - 1] if bet_num <= len(bet_sizes) else bet_sizes[-1]

            state.bet_windows.append(BetWindow(
                bet_number=bet_num,
                start_tick=start_tick,
                end_tick=end_tick,
                bet_size=bet_size,
                outcome="pending" if state.game_duration >= start_tick else "skipped",
            ))

    def tick(self, session_id: str) -> dict:
        """
        Advance one tick in playback.

        Returns:
            Dict with tick result and updated state
        """
        state = self._sessions.get(session_id)
        if not state:
            return {"error": "Session not found"}

        strategy = self._strategies.get(session_id, {})

        # Advance tick
        state.current_tick += 1

        # Update price
        if state.current_tick < len(state.prices):
            state.current_price = state.prices[state.current_tick]

        # Check bet window outcomes
        self._check_bet_outcomes(state)

        # Check game end
        if state.current_tick >= state.game_duration:
            self._finalize_game(state)
            return {
                "game_ended": True,
                "state": state.to_dict(),
            }

        return {
            "game_ended": False,
            "state": state.to_dict(),
        }

    def _check_bet_outcomes(self, state: PlaybackState):
        """Check and update bet window outcomes"""
        for bw in state.bet_windows:
            if bw.outcome != "pending":
                continue

            # Check if we're in this bet's window and game rugged
            if bw.start_tick <= state.game_duration < bw.end_tick:
                if state.current_tick >= state.game_duration:
                    # Rug happened during this window - WIN
                    bw.outcome = "win"
                    bw.payout = bw.bet_size * 5
                    state.current_balance += bw.payout - bw.bet_size
                    state.total_wins += 1
            elif state.current_tick >= bw.end_tick:
                # Window ended without rug - LOSS
                bw.outcome = "loss"
                state.current_balance -= bw.bet_size
                state.total_losses += 1

        # Update peak
        if state.current_balance > state.peak_balance:
            state.peak_balance = state.current_balance

    def _finalize_game(self, state: PlaybackState):
        """Finalize a game and prepare for next"""
        state.games_played += 1
        state.status = PlaybackStatus.PAUSED

    def next_game(self, session_id: str) -> dict:
        """Load next game in sequence"""
        state = self._sessions.get(session_id)
        if not state:
            return {"error": "Session not found"}

        strategy = self._strategies.get(session_id, {})

        # Move to next game
        next_idx = state.current_game_idx + 1
        if next_idx >= len(self._validation_games):
            state.status = PlaybackStatus.COMPLETED
            return {"completed": True, "state": state.to_dict()}

        self._load_game(state, next_idx, strategy)
        return {"state": state.to_dict()}
```

### 3. Playback Controls

```python
def pause(self, session_id: str):
    """Pause playback"""
    state = self._sessions.get(session_id)
    if state:
        state.status = PlaybackStatus.PAUSED

def resume(self, session_id: str):
    """Resume playback"""
    state = self._sessions.get(session_id)
    if state:
        state.status = PlaybackStatus.PLAYING

def set_speed(self, session_id: str, multiplier: float):
    """Set playback speed (0.5x to 4x)"""
    state = self._sessions.get(session_id)
    if state:
        state.speed_multiplier = max(0.5, min(4.0, multiplier))

def get_state(self, session_id: str) -> PlaybackState | None:
    """Get current playback state"""
    return self._sessions.get(session_id)

def stop_session(self, session_id: str):
    """Stop and remove a session"""
    if session_id in self._sessions:
        del self._sessions[session_id]
    if session_id in self._strategies:
        del self._strategies[session_id]
```

### 4. Strategy Persistence

```python
def save_strategy(self, strategy: dict) -> str:
    """Save strategy to file"""
    name = strategy.get("name")
    if not name:
        raise ValueError("Strategy must have a name")

    filepath = self._strategies_dir / f"{name}.json"
    with open(filepath, "w") as f:
        json.dump(strategy, f, indent=2)
    return name

def load_strategy(self, name: str) -> dict | None:
    """Load strategy by name"""
    filepath = self._strategies_dir / f"{name}.json"
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return json.load(f)

def list_strategies(self) -> list[dict]:
    """List all saved strategies"""
    strategies = []
    for filepath in self._strategies_dir.glob("*.json"):
        with open(filepath) as f:
            strategy = json.load(f)
            strategies.append({
                "name": strategy.get("name", filepath.stem),
                "entry_tick": strategy.get("entry_tick", 200),
                "num_bets": strategy.get("num_bets", 4),
            })
    return strategies
```

### 5. API Endpoints

```python
# src/recording_ui/app.py

@app.route("/api/backtest/start", methods=["POST"])
def api_start_backtest():
    """Start a new backtest playback session"""
    service = get_backtest_service()
    data = request.get_json() or {}

    # Can pass strategy by name or inline
    if "strategy_name" in data:
        strategy = service.load_strategy(data["strategy_name"])
        if not strategy:
            return jsonify({"error": "Strategy not found"}), 404
    else:
        strategy = data.get("strategy", data)

    session_id = service.start_playback(strategy)
    state = service.get_state(session_id)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "state": state.to_dict() if state else None,
    })

@app.route("/api/backtest/tick/<session_id>", methods=["POST"])
def api_backtest_tick(session_id: str):
    """Advance one tick"""
    service = get_backtest_service()
    result = service.tick(session_id)
    return jsonify(result)

@app.route("/api/backtest/control/<session_id>", methods=["POST"])
def api_backtest_control(session_id: str):
    """Control playback (pause/resume/speed/next)"""
    service = get_backtest_service()
    data = request.get_json() or {}
    action = data.get("action")

    if action == "pause":
        service.pause(session_id)
    elif action == "resume":
        service.resume(session_id)
    elif action == "speed":
        service.set_speed(session_id, float(data.get("value", 1.0)))
    elif action in ("next", "next_game"):
        service.next_game(session_id)
    elif action == "stop":
        service.stop_session(session_id)
        return jsonify({"success": True, "stopped": True})

    state = service.get_state(session_id)
    return jsonify(state.to_dict() if state else {"stopped": True})
```

## Frontend Integration

### JavaScript Playback Controller

```javascript
// static/js/backtest.js

class BacktestPlayer {
    constructor() {
        this.sessionId = null;
        this.state = null;
        this.interval = null;
        this.baseTickRate = 250;  // 250ms per tick at 1x
    }

    async start(strategy) {
        const response = await fetch('/api/backtest/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({strategy})
        });
        const data = await response.json();
        this.sessionId = data.session_id;
        this.state = data.state;
        this.updateDisplay();
        return this.sessionId;
    }

    play() {
        if (this.interval) return;
        const tickRate = this.baseTickRate / (this.state.speed_multiplier || 1);
        this.interval = setInterval(() => this.tick(), tickRate);
    }

    pause() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    async tick() {
        const response = await fetch(`/api/backtest/tick/${this.sessionId}`, {
            method: 'POST'
        });
        const data = await response.json();
        this.state = data.state;
        this.updateDisplay();

        if (data.game_ended) {
            this.pause();
            this.showGameEndOverlay();
        }
    }

    updateDisplay() {
        // Update tick counter
        document.getElementById('tick').textContent = this.state.current_tick;

        // Update price
        document.getElementById('price').textContent =
            this.state.current_price.toFixed(2) + 'x';

        // Update chart
        this.updateChart();

        // Update bet windows
        this.updateBetWindows();

        // Update session stats
        this.updateStats();
    }

    updateChart() {
        const ctx = this.chart.ctx;
        // Draw price line up to current tick
        // Highlight bet windows
        // Mark rug point if occurred
    }
}
```

## Gotchas

1. **Price Array Indexing**: Prices array is 0-indexed. Tick 0 = prices[0].

2. **Bet Window Timing**: 40-tick window + 5-tick cooldown = 45 ticks between starts.

3. **Early Rug**: If game rugs before entry_tick, bet windows are "skipped", not "pending".

4. **Balance Update**: Update balance on outcome determination, not on tick advance.

5. **Speed Scaling**: Frontend controls tick rate via setInterval, not backend.

6. **Session Cleanup**: Call stop_session when done to free memory.

7. **Game Order**: Games in validation set may be shuffled or sorted by duration.
