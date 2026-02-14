# 00 - Architecture Overview

## Purpose

VECTRA-PLAYER is a comprehensive trading system for rugs.fun sidebet optimization. It provides:
1. Real-time game data capture via Chrome DevTools Protocol (CDP)
2. WebSocket event interception and normalization
3. Statistical analysis and Monte Carlo simulation
4. Live and backtested strategy execution
5. Reinforcement learning environment for agent training

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VECTRA-PLAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────┐     ┌────────────────────────┐   │
│  │   Chrome    │────▶│  CDP Interceptor │────▶│     Event Normalizer   │   │
│  │  (rugs.fun) │     │  (WebSocket)     │     │   (Foundation Service) │   │
│  └─────────────┘     └─────────────────┘     └───────────┬────────────┘   │
│                                                          │                 │
│                                              ┌───────────▼────────────┐   │
│                                              │       EventBus         │   │
│                                              │  (Pub/Sub Messaging)   │   │
│                                              └───────────┬────────────┘   │
│                                                          │                 │
│          ┌──────────────────┬──────────────────┬────────┴───────┐        │
│          │                  │                  │                │        │
│          ▼                  ▼                  ▼                ▼        │
│  ┌───────────────┐  ┌─────────────┐  ┌────────────────┐ ┌─────────────┐ │
│  │  EventStore   │  │  Dashboard  │  │ Live Backtest  │ │  Browser    │ │
│  │  (Parquet)    │  │  (Flask)    │  │   Service      │ │  Service    │ │
│  └───────────────┘  └─────────────┘  └────────────────┘ └─────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

                    ┌───────────────────────────────────────┐
                    │         Analysis & Optimization        │
                    ├───────────────────────────────────────┤
                    │  - Monte Carlo Simulation (10k iter)  │
                    │  - Kelly Criterion (8 variants)       │
                    │  - Bayesian Rug Signal Detection      │
                    │  - Survival Analysis                  │
                    │  - RL Environment (Gymnasium)         │
                    └───────────────────────────────────────┘
```

## Data Flow

### 1. Event Capture Pipeline

```
Browser (rugs.fun) → CDP Session → WebSocket Interceptor → Event Normalizer
                                                                  │
                                    ┌─────────────────────────────┘
                                    ▼
                             EventBus.publish(WS_RAW_EVENT)
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
   EventStore               BrowserService            LiveBacktestService
   (Persistence)            (UI Updates)              (Paper Trading)
```

### 2. Trading Action Pipeline

```
Dashboard UI → Flask API → BrowserService → BrowserBridge → CDP → Chrome
                                                                    │
                                                                    ▼
                                                            rugs.fun Button Click
```

## Key Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **BrowserBridge** | `src/browser/bridge.py` | CDP connection, button click mapping |
| **EventNormalizer** | `src/foundation/normalizer.py` | Raw → normalized event transformation |
| **EventBus** | `src/services/event_bus.py` | Pub/sub event distribution |
| **EventStore** | `src/services/event_store/` | Parquet persistence (single writer) |
| **Flask App** | `src/recording_ui/app.py` | Dashboard, REST API, SocketIO |
| **BrowserService** | `src/recording_ui/services/browser_service.py` | Flask ↔ Bridge adapter |
| **BacktestService** | `src/recording_ui/services/backtest_service.py` | Historical replay |
| **LiveBacktestService** | `src/recording_ui/services/live_backtest_service.py` | Paper trading |
| **MonteCarloSimulator** | `src/recording_ui/services/monte_carlo.py` | 10k iteration engine |
| **PositionSizing** | `src/recording_ui/services/position_sizing.py` | Kelly variants |
| **BayesianRugSignal** | `src/analysis/bayesian_rug_signal.py` | Real-time rug probability |
| **SidebetV1Env** | `src/rl/envs/sidebet_v1_env.py` | Gymnasium RL environment |

## Critical Constants

| Constant | Value | Source |
|----------|-------|--------|
| Sidebet payout | 5:1 (400% profit) | rugs.fun mechanics |
| Sidebet window | 40 ticks | Protocol spec |
| Cooldown between bets | 5 ticks | Protocol spec |
| Breakeven win rate | 16.67% (1/6) | Mathematical |
| Optimal entry zone | Tick 200+ | Historical analysis |
| Event gap signal | 500ms+ = high confidence | Bayesian analysis |
| Tick interval | ~250ms | Empirical |

## Event Types (Normalized)

| rugs.fun Event | Foundation Type | Data |
|----------------|-----------------|------|
| `gameStateUpdate` | `game.tick` | price, tickCount, active, rugged |
| `playerUpdate` | `player.state` | cash, positionQty, avgCost |
| `usernameStatus` | `connection.authenticated` | player_id, username |
| `standard/newTrade` | `player.trade` | username, type, qty, price |
| `currentSidebet` | `sidebet.placed` | bet details |
| `currentSidebetResult` | `sidebet.result` | outcome |

## Game Phases

```
COOLDOWN → PRESALE → ACTIVE → RUGGED
    │                   │
    │                   ├── Sidebet window opens at entry_tick
    │                   └── Rug terminates game
    └── Countdown timer > 0
```

## Directory Structure

```
VECTRA-PLAYER/
├── src/
│   ├── browser/           # CDP integration layer
│   │   ├── bridge.py      # BrowserBridge singleton
│   │   └── manager.py     # CDPBrowserManager
│   ├── foundation/        # Event normalization service
│   │   ├── broadcaster.py # WebSocket broadcaster
│   │   ├── normalizer.py  # Event transformation
│   │   └── launcher.py    # Service startup
│   ├── services/          # Core services
│   │   ├── event_bus.py   # Pub/sub messaging
│   │   └── event_store/   # Parquet persistence
│   ├── recording_ui/      # Flask dashboard
│   │   ├── app.py         # Routes and SocketIO
│   │   ├── services/      # Business logic
│   │   ├── templates/     # Jinja2 HTML
│   │   └── static/        # CSS/JS
│   ├── analysis/          # Statistical modules
│   │   └── bayesian_rug_signal.py
│   └── rl/                # Reinforcement learning
│       └── envs/          # Gymnasium environments
└── docs/
    └── Statistical Opt/   # This documentation
```

## Dependencies

### Core Python Packages
- `flask` + `flask-socketio`: Web dashboard
- `playwright`: Browser automation
- `pandas` + `numpy`: Data processing
- `duckdb` + `pyarrow`: Parquet storage
- `gymnasium`: RL environment
- `stable-baselines3`: RL algorithms (optional)

### External Services
- Chrome browser with CDP (port 9222)
- rugs.fun WebSocket (wss://rugs.fun)

## Integration Points

### CDP → EventBus
```python
# In BrowserBridge._start_cdp_interception()
def on_cdp_event(event):
    self._event_bus.publish(Events.WS_RAW_EVENT, event)
```

### EventBus → EventStore
```python
# In EventStoreService.start()
self._event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event)
```

### Flask → BrowserBridge
```python
# In app.py
browser_service = get_browser_service(socketio)
# BrowserService wraps BrowserBridge for sync/async bridging
```

## Gotchas

1. **Chrome Profile**: Must use `rugs_bot` profile at `~/.gamebot/chrome_profiles/rugs_bot/` - Default profile has CDP issues

2. **WebSocket Reconnection**: Pre-existing WebSockets can't be intercepted by CDP. Force Socket.IO reconnect after CDP setup.

3. **Event Double-Wrapping**: EventBus wraps events, so handlers must unwrap: `data = wrapped.get("data", wrapped)`

4. **Single Writer**: Only EventStoreService writes to Parquet. All other services publish to EventBus.

5. **Thread Safety**: BrowserBridge uses async queue for thread-safe bridging between Flask (sync) and Playwright (async)

6. **Reloader Guard**: Flask debug reloader creates duplicate processes. Check `WERKZEUG_RUN_MAIN` before starting services.
