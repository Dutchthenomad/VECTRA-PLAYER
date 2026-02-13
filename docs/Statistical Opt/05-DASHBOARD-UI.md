# 05 - Dashboard UI

## Purpose

Flask-based web dashboard for:
1. Recording control and monitoring
2. Strategy exploration and analysis
3. Live and backtested trading
4. Trading profile management

## Dependencies

```python
# Web framework
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

# Internal services
from recording_ui.services.browser_service import get_browser_service
from recording_ui.services.backtest_service import get_backtest_service
from recording_ui.services.live_backtest_service import get_live_backtest_service
from recording_ui.services.profile_service import get_profile_service
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Flask Dashboard                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          Flask Routes                                │   │
│  │  /              → dashboard.html                                    │   │
│  │  /explorer      → explorer.html    (Strategy analysis)              │   │
│  │  /backtest      → backtest.html    (Replay/Live trading)           │   │
│  │  /profiles      → profiles.html    (Trading profiles)              │   │
│  │  /models        → models.html      (ML training metrics)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          REST API                                    │   │
│  │  /api/status             → Recording status                         │   │
│  │  /api/recording/toggle   → Start/stop recording                     │   │
│  │  /api/browser/*          → CDP connection, button clicks            │   │
│  │  /api/explorer/*         → Strategy stats, simulation               │   │
│  │  /api/backtest/*         → Playback control                         │   │
│  │  /api/profiles/*         → CRUD profiles                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SocketIO Events                              │   │
│  │  join_live    → Start live paper trading session                    │   │
│  │  leave_live   → Stop session                                        │   │
│  │  live_tick    → Real-time game updates (server → client)           │   │
│  │  game_state   → Current game state (server → client)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Flask App Initialization

```python
# src/recording_ui/app.py

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)

# SocketIO with eventlet for async support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Initialize services with SocketIO for real-time updates
browser_service = get_browser_service(socketio)
live_backtest_service = get_live_backtest_service(socketio)
```

### 2. Service Startup Guard

Prevent duplicate startup in Flask debug reloader:

```python
_services_started = False

def _start_background_services():
    """Start services once (guard against reloader duplicates)"""
    global _services_started
    if _services_started:
        return

    # WERKZEUG_RUN_MAIN is 'true' in child process
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        event_bus.start()
        event_store_service = EventStoreService(event_bus)
        event_store_service.start()
        _services_started = True
    else:
        logger.info("Skipping service startup in reloader parent")

_start_background_services()
```

### 3. REST API Patterns

```python
# Status endpoint
@app.route("/api/status")
def get_status():
    return jsonify({
        "is_recording": event_store_service.is_recording,
        "event_count": event_store_service.event_count,
        "game_count": len(event_store_service.recorded_game_ids),
    })

# Toggle recording
@app.route("/api/recording/toggle", methods=["POST"])
def toggle_recording():
    is_recording = event_store_service.toggle_recording()
    return jsonify({"success": True, "is_recording": is_recording})

# Browser connection
@app.route("/api/browser/connect", methods=["POST"])
def browser_connect():
    result = browser_service.connect()
    return jsonify(result)

# Trading action
@app.route("/api/trade/buy", methods=["POST"])
def trade_buy():
    result = browser_service.click_buy()
    return jsonify(result)
```

### 4. SocketIO Real-Time Updates

```python
# Client joins live trading session
@socketio.on("join_live")
def handle_join_live(data):
    session_id = data.get("session_id")
    strategy = data.get("strategy", {})

    # Join room for this session
    join_room(session_id)

    # Start paper trading session
    session = live_backtest_service.start_session(session_id, strategy)

    # Connect to WebSocket feed
    live_backtest_service.ensure_ws_connected()

    # Send initial state
    emit("live_joined", {
        "session_id": session_id,
        "session": session.to_dict()
    })

# Client leaves session
@socketio.on("leave_live")
def handle_leave_live(data):
    session_id = data.get("session_id")
    if session_id:
        leave_room(session_id)
        live_backtest_service.stop_session(session_id)
```

### 5. BrowserService SocketIO Integration

```python
# src/recording_ui/services/browser_service.py

class BrowserService:
    def __init__(self, socketio=None):
        self._socketio = socketio

        # Subscribe to EventBus for game state
        event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_event, weak=False)

    def _handle_game_state(self, data: dict):
        """Forward game state to SocketIO clients"""
        with self._lock:
            self._game_state.tick_count = data.get("tickCount", 0)
            self._game_state.price = float(data.get("price", 1.0))
            self._game_state.phase = self._detect_phase(data)

        if self._socketio:
            self._socketio.emit("game_state", {
                "tick_count": self._game_state.tick_count,
                "price": self._game_state.price,
                "phase": self._game_state.phase,
            })
```

### 6. Explorer API with Simulation

```python
@app.route("/api/explorer/simulate", methods=["POST"])
def api_explorer_simulate():
    """Run bankroll simulation"""
    data = request.get_json() or {}

    config = position_sizing.WalletConfig(
        initial_balance=data.get("initial_balance", 0.1),
        entry_tick=data.get("entry_tick", 200),
        bet_sizes=data.get("bet_sizes", [0.001] * 4),
        max_drawdown_pct=data.get("max_drawdown_pct", 0.50),
        use_kelly_sizing=data.get("use_kelly_sizing", False),
        kelly_fraction=data.get("kelly_fraction", 0.25),
    )

    games_df = explorer_data.load_games_df()
    result = position_sizing.run_simulation(games_df, config)

    return jsonify(position_sizing.simulation_to_dict(result))
```

### 7. Monte Carlo Comparison API

```python
@app.route("/api/explorer/monte-carlo", methods=["POST"])
def api_explorer_monte_carlo():
    """Run Monte Carlo comparison across all strategies"""
    from .services.monte_carlo_service import run_strategy_comparison

    data = request.get_json() or {}
    num_iterations = data.get("num_iterations", 10000)

    # Only allow 1k, 10k, 100k
    if num_iterations not in [1000, 10000, 100000]:
        num_iterations = 10000

    results = run_strategy_comparison(
        num_iterations=num_iterations,
        initial_bankroll=data.get("initial_bankroll", 0.1),
        win_rate=data.get("win_rate", 0.185),
    )

    return jsonify(results)
```

## Dashboard Tabs

### Recording Tab (/)
- Start/stop recording toggle
- Event count, game count display
- Recent games list

### Explorer Tab (/explorer)
- Strategy parameter controls (entry_tick, num_bets)
- Win rate visualization by cumulative bets
- Duration histogram
- Bankroll simulation
- Monte Carlo comparison

### Backtest Tab (/backtest)
- Strategy selection
- Playback controls (play/pause/speed)
- Live mode toggle
- Real-time game chart
- Trading buttons (BUY/SELL/SIDEBET)

### Profiles Tab (/profiles)
- Trading profile CRUD
- Import from Monte Carlo
- MC metrics display

## Integration Points

### With EventBus

```python
# BrowserService subscribes for game state
event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_event, weak=False)
```

### With EventStoreService

```python
# Direct toggle (same process)
event_store_service.toggle_recording()

# Status via IPC file (optional)
# Reads .recording_status.json
```

### With BrowserBridge

```python
# Via BrowserService wrapper
browser_service = get_browser_service(socketio)
browser_service.click_buy()  # Queues async CDP click
```

## Configuration

### Environment Variables

```bash
PORT=5000              # Flask port
FLASK_DEBUG=false      # Debug mode (enables reloader)
```

### SocketIO Settings

```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Or restrict to localhost
    async_mode="eventlet"      # Required for threading
)
```

### Run Command

```bash
# Development
python -m recording_ui.app --port 5000 --debug

# Production
python -m recording_ui.app --no-browser
```

## Frontend JavaScript Patterns

### SocketIO Client

```javascript
// static/js/backtest.js

const socket = io();

// Join live session
socket.emit('join_live', {
    session_id: 'session-' + Date.now(),
    strategy: currentStrategy
});

// Handle live ticks
socket.on('live_tick', (data) => {
    updateGameChart(data.tick);
    updateSessionStats(data.session);
});

// Handle game state updates
socket.on('game_state', (data) => {
    document.getElementById('tick').textContent = data.tick_count;
    document.getElementById('price').textContent = data.price.toFixed(2) + 'x';
    document.getElementById('phase').textContent = data.phase;
});
```

### API Calls

```javascript
// Start backtest
async function startBacktest() {
    const response = await fetch('/api/backtest/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({strategy: currentStrategy})
    });
    return response.json();
}

// Execute trade
async function executeBuy() {
    await fetch('/api/trade/buy', {method: 'POST'});
}
```

## Gotchas

1. **Eventlet Mode**: SocketIO requires `async_mode="eventlet"` for threading compatibility.

2. **allow_unsafe_werkzeug**: Required for socketio.run() with threading mode.

3. **Reloader Guard**: Check `WERKZEUG_RUN_MAIN` to prevent duplicate service startup.

4. **CORS**: Set `cors_allowed_origins="*"` for development, restrict in production.

5. **Room-based Events**: Use join_room/leave_room for session-specific SocketIO events.

6. **Service Singletons**: Use get_*_service() functions to ensure single instances.

7. **Chrome Tab Opener**: Auto-opens dashboard in Chrome after Flask starts (with delay).
