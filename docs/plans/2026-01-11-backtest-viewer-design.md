# Backtest Viewer Design

**Date:** 2026-01-11
**Status:** Approved
**Purpose:** Visual strategy backtesting with real-time playback on recorded game data

---

## Overview

A new tab in the Game Explorer that allows users to:
1. Watch a saved strategy execute on recorded games with speed controls
2. Validate strategies on unseen data (train/validation split)
3. See bet placement, wallet changes, and outcomes as they happen
4. Eventually connect to live feed for dry-run validation

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BACKTEST VIEWER                                     [Speed: ▐████░░░░] │
│  Strategy: "Kelly-55-2x" ▾    [Load] [Save] [New]   1x  2x  5x  10x MAX │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     PRICE CHART                   ┌────────────┐ │   │
│  │  Price                                            │ TICK: 247  │ │   │
│  │   2.0x ┤                          ╭─╮             │ PRICE: 1.82│ │   │
│  │   1.5x ┤                      ╭───╯ │             └────────────┘ │   │
│  │   1.0x ┼──────────────────────╯     ╰──╮  ◆ BET 1               │   │
│  │   0.5x ┤                               ╰─── ★ RUG               │   │
│  │        └──────────────────────────────────────────────────────────   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  WALLET STATUS          │  │  CUMULATIVE STATS                    │   │
│  │  Balance: 0.1342 SOL    │  │  Games: 47/283   Win Rate: 63.8%    │   │
│  │  P&L: +34.2%            │  │  Wins: 30  Losses: 17               │   │
│  │  Active Bets:           │  │  Max DD: 12.3%                      │   │
│  │  ◆ Bet 1: 0.0034 SOL    │  │  [▓▓▓▓▓▓▓░░░░░░░░] 47/283          │   │
│  └─────────────────────────┘  └─────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  EQUITY CURVE                                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Visual Elements

- **◆ Filled diamond** = Active bet (SOL deducted)
- **◇ Open diamond** = Pending bet window
- **★ Star** = Rug point (win/loss resolved)
- **Shaded regions** = 40-tick bet windows
- **Digital ticker** = Current tick and price as integers

---

## Data Architecture

### 1. Strategy Configurations

Stored in `~/rugs_data/strategies/*.json`:

```json
{
  "name": "Kelly-55-2x",
  "created": "2026-01-11T16:30:00Z",
  "params": {
    "entry_tick": 219,
    "num_bets": 4,
    "use_kelly_sizing": true,
    "kelly_fraction": 0.25,
    "use_dynamic_sizing": true,
    "high_confidence_threshold": 55,
    "high_confidence_multiplier": 2.0,
    "reduce_on_drawdown": true,
    "max_drawdown_pct": 0.15,
    "take_profit_target": 1.3
  },
  "initial_balance": 0.1
}
```

### 2. Game Data Split

- **Training set (70%)**: Used in Explorer for strategy tuning
- **Validation set (30%)**: Held out for backtest viewer
- Split is deterministic (hash-based on game_id)

### 3. Game Data Source

From `~/rugs_data/events_parquet/doc_type=complete_game/`:
- `game_id`: Unique identifier
- `prices`: Array of tick-by-tick price multipliers (starts at 1.0)
- `duration`: len(prices) = total ticks

---

## Playback Engine

### Backend Service: `backtest_service.py`

```python
@dataclass
class PlaybackState:
    strategy: dict
    games: List[dict]
    current_game_idx: int = 0
    current_tick: int = 0
    wallet: float = 0.1
    active_bets: List[dict] = field(default_factory=list)
    cumulative_stats: dict = field(default_factory=dict)
    paused: bool = True

class BacktestService:
    def load_strategy(self, name: str) -> dict
    def save_strategy(self, strategy: dict) -> str
    def list_strategies(self) -> List[str]
    def start_playback(self, strategy_name: str) -> str  # returns session_id
    def tick(self, session_id: str) -> PlaybackState
    def set_speed(self, session_id: str, speed: float)
    def pause(self, session_id: str)
    def resume(self, session_id: str)
    def next_game(self, session_id: str)
```

### Speed Control

| Speed | Tick Interval | Description |
|-------|---------------|-------------|
| 1x    | 250ms         | Real-time   |
| 2x    | 125ms         | Double      |
| 5x    | 50ms          | Fast        |
| 10x   | 25ms          | Very fast   |
| MAX   | 0ms           | Instant     |

### API Endpoints

```
GET  /api/backtest/strategies         # List saved strategies
GET  /api/backtest/strategies/<name>  # Load strategy
POST /api/backtest/strategies         # Save strategy
POST /api/backtest/start              # Start playback session
GET  /api/backtest/state/<session_id> # Get current state (SSE stream)
POST /api/backtest/control            # pause/resume/speed/next
```

---

## Playback Modes

### Mode 1: Historical Backtest (MVP)

- Replays recorded games from parquet
- Speed slider controls playback rate
- Pause, step, skip to next game
- Uses validation set only

### Mode 2: Live Dry-Run (Future)

- Connects to live WebSocket feed
- Strategy makes virtual decisions
- No real money - simulated wallet
- Proves real-world viability

---

## Implementation Plan

### Phase 1: Backend (backtest_service.py)
1. Strategy save/load from JSON files
2. Game data loader with train/validation split
3. Playback state machine
4. Tick-by-tick simulation with bet logic

### Phase 2: API Routes
1. Strategy CRUD endpoints
2. Playback control endpoints
3. Server-Sent Events for state streaming

### Phase 3: Frontend (backtest.html + backtest.js)
1. Price chart with playhead animation
2. Digital ticker overlay
3. Wallet status panel
4. Cumulative stats panel
5. Equity curve (builds over time)
6. Speed controls and playback buttons

### Phase 4: Polish
1. Strategy presets from Explorer
2. Export results to CSV
3. Compare multiple strategies

---

## File Structure

```
src/recording_ui/
├── services/
│   └── backtest_service.py    # NEW
├── templates/
│   └── backtest.html          # NEW
├── static/js/
│   └── backtest.js            # NEW
└── app.py                     # Add routes

~/rugs_data/
└── strategies/                # NEW - saved strategies
    └── *.json
```
