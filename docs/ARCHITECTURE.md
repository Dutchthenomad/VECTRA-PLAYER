# VECTRA-PLAYER System Architecture

**Version:** 2.0.0
**Date:** 2026-01-17
**Status:** Production + Foundation Service (pending merge)

---

## Overview

VECTRA-PLAYER is a data capture and analysis platform for rugs.fun, built on a unified event-driven architecture.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER INTERFACES                                    │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Recording UI    │  │ Foundation      │  │ HTML Artifacts              │  │
│  │ (Flask :5000)   │  │ Monitor (:9001) │  │ (served via :9001)          │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
│           │                    │                          │                  │
└───────────┼────────────────────┼──────────────────────────┼──────────────────┘
            │                    │                          │
            ▼                    ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                         │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Browser Service │  │ Foundation      │  │ EventBus                    │  │
│  │ (CDP Control)   │  │ Service         │  │ (Pub/Sub)                   │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
│           │                    │                          │                  │
└───────────┼────────────────────┼──────────────────────────┼──────────────────┘
            │                    │                          │
            ▼                    ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                            │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ CDP Interceptor │  │ Event Normalizer│  │ EventStore                  │  │
│  │ (WebSocket)     │──▶│ (Foundation)    │──▶│ (Parquet Writer)           │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┬──────────────┘  │
│                                                            │                  │
│                                                            ▼                  │
│                                            ┌─────────────────────────────┐   │
│                                            │ Parquet Files               │   │
│                                            │ ~/rugs_data/events_parquet/ │   │
│                                            └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Chrome DevTools Protocol (CDP) Layer

**Purpose:** Intercept WebSocket traffic between browser and rugs.fun

```
Browser (Chrome)
    │
    │ WebSocket to rugs.fun
    ▼
┌─────────────────────┐
│ CDPWebSocketInterceptor │
│ - Attaches to Chrome via CDP
│ - Discovers Socket.IO connection
│ - Intercepts all frames
└──────────┬──────────┘
           │
           ▼
     EventBus.publish(WS_RAW_EVENT)
```

**Key Files:**
- `src/services/cdp_websocket_interceptor.py`
- `src/services/browser_bridge.py`

**Configuration:**
```python
CDP_PORT = 9222  # Chrome debugging port
CHROME_PROFILE = "rugs_bot"  # ~/.gamebot/chrome_profiles/rugs_bot/
```

### 2. Recording UI (Flask)

**Purpose:** Web dashboard for recording control and trading

**Port:** 5000

**Routes:**
| Route | Purpose |
|-------|---------|
| `/` | Dashboard home |
| `/recording` | Recording tab |
| `/explorer` | Strategy analysis |
| `/backtest` | Live trading view |
| `/profiles` | Profile management |
| `/api/*` | REST endpoints |

**Key Files:**
- `src/recording_ui/app.py` - Flask app
- `src/recording_ui/services/browser_service.py` - CDP integration
- `src/recording_ui/templates/*.html` - Jinja2 templates
- `src/recording_ui/static/js/*.js` - Frontend JavaScript

### 3. Foundation Service (Feature Branch)

**Purpose:** Unified WebSocket broadcaster for HTML artifacts

**Ports:**
- WebSocket Broadcaster: 9000
- HTTP Monitor: 9001

**Architecture:**
```
rugs.fun WebSocket (via CDP)
    │
    ▼
┌─────────────────────┐
│ EventNormalizer     │
│ - Maps event types  │
│ - Unifies structure │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ WebSocketBroadcaster│
│ - Accepts clients   │
│ - Broadcasts events │
│ ws://localhost:9000 │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Connected Clients   │
│ - HTML Artifacts    │
│ - Orchestrator      │
│ - Custom tools      │
└─────────────────────┘
```

**Event Type Mapping:**
| rugs.fun Event | Foundation Type |
|----------------|-----------------|
| `gameStateUpdate` | `game.tick` |
| `playerUpdate` | `player.state` |
| `usernameStatus` | `connection.authenticated` |
| `standard/newTrade` | `player.trade` |
| `currentSidebet` | `sidebet.placed` |
| `currentSidebetResult` | `sidebet.result` |

**Key Files (on feature branch):**
- `src/foundation/config.py` - Configuration with env vars
- `src/foundation/normalizer.py` - Event type normalization
- `src/foundation/broadcaster.py` - WebSocket server
- `src/foundation/http_server.py` - Monitor UI
- `src/foundation/launcher.py` - Full startup with Chrome

### 4. EventBus (Pub/Sub)

**Purpose:** Decouple event producers from consumers

**Event Types:**
```python
class Events(Enum):
    WS_RAW_EVENT = "ws_raw_event"
    GAME_TICK = "game_tick"
    PLAYER_UPDATE = "player_update"
    BUTTON_PRESS = "button_press"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
```

**Key File:** `src/services/event_bus.py`

### 5. EventStore (Persistence)

**Purpose:** Write events to Parquet files

**Schema Version:** 2.0.0

**DocTypes:**
| DocType | Source Event | Purpose |
|---------|--------------|---------|
| `ws_event` | WS_RAW_EVENT | Raw WebSocket events |
| `game_tick` | GAME_TICK | Price/tick stream |
| `player_action` | BUTTON_PRESS | Human/bot actions |
| `server_state` | PLAYER_UPDATE | Balance/position snapshots |
| `system_event` | CONNECTION_* | Connection state changes |

**Storage Path:** `~/rugs_data/events_parquet/doc_type=<type>/`

**Key Files:**
- `src/services/event_store/writer.py` - Buffering, atomic writes
- `src/services/event_store/schema.py` - Pydantic models
- `src/services/event_store/paths.py` - Directory resolution

### 6. LiveStateProvider

**Purpose:** Maintain current game state from WebSocket events

**Tracked State:**
- `tick` - Current tick number
- `price` - Current price
- `game_id` - Current game identifier
- `game_phase` - BETTING, LIVE, COOLDOWN
- `balance` - Player balance
- `position_qty` - Position quantity
- `entry_tick` - When position was opened
- `time_in_position` - Ticks since entry

**Key File:** `src/services/live_state_provider.py`

---

## Data Flow

### Recording Flow

```
1. User clicks "Start Recording" in UI
   │
   ▼
2. Flask → EventBus.publish(RECORDING_STARTED)
   │
   ▼
3. EventStore subscribes, begins buffering
   │
   ▼
4. CDP Interceptor captures WebSocket frames
   │
   ▼
5. Events flow: CDP → EventBus → EventStore → Parquet
   │
   ▼
6. User clicks "Stop Recording"
   │
   ▼
7. EventStore flushes buffer, writes final Parquet file
```

### Trading Flow

```
1. User clicks BUY/SELL in Backtest tab
   │
   ▼
2. BrowserService executes via CDP
   │
   ▼
3. Button click dispatched to rugs.fun page
   │
   ▼
4. ButtonEvent emitted with game context
   │
   ▼
5. EventStore persists player_action
```

### Foundation Service Flow (after merge)

```
1. Foundation launcher starts Chrome + CDP
   │
   ▼
2. CDP intercepts rugs.fun WebSocket
   │
   ▼
3. EventNormalizer transforms to Foundation types
   │
   ▼
4. Broadcaster sends to all connected clients
   │
   ▼
5. HTML artifacts receive game.tick, player.state, etc.
```

---

## Directory Structure

```
VECTRA-PLAYER/
├── src/
│   ├── core/                    # Core game logic
│   │   └── game_state.py
│   ├── services/                # Infrastructure services
│   │   ├── event_bus.py
│   │   ├── event_store/
│   │   ├── live_state_provider.py
│   │   ├── browser_bridge.py
│   │   └── cdp_websocket_interceptor.py
│   ├── foundation/              # (feature branch) WebSocket broadcaster
│   │   ├── config.py
│   │   ├── normalizer.py
│   │   ├── broadcaster.py
│   │   └── launcher.py
│   ├── recording_ui/            # Flask dashboard
│   │   ├── app.py
│   │   ├── services/
│   │   ├── templates/
│   │   └── static/
│   ├── models/                  # Data models
│   │   └── events/
│   ├── artifacts/               # (planned) HTML tools
│   │   ├── shared/
│   │   ├── tools/
│   │   └── orchestrator/
│   └── rugs_recordings/         # Analysis tools
│       └── PRNG CRAK/
├── docs/
│   ├── STATUS.md
│   ├── ARCHITECTURE.md
│   ├── plans/
│   └── specs/
├── scripts/
│   └── start.sh
└── tests/
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `RUGS_DATA_DIR` | `~/rugs_data` | Data storage root |
| `CHROME_PROFILE` | `rugs_bot` | Chrome profile name |
| `CDP_PORT` | `9222` | Chrome debugging port |
| `FOUNDATION_PORT` | `9000` | WebSocket broadcaster |
| `FOUNDATION_HTTP_PORT` | `9001` | Monitor UI |
| `FOUNDATION_HEADLESS` | `false` | Headless Chrome mode |

---

## Integration Points

### External Systems

| System | Purpose | Location |
|--------|---------|----------|
| rugs.fun | Trading platform | https://rugs.fun |
| ChromaDB | Vector storage | ~/Desktop/claude-flow/rag-pipeline/storage/chroma/ |
| rugs-expert MCP | Protocol knowledge | Remote MCP server |

### Related Repositories

| Repository | Purpose |
|------------|---------|
| claude-flow | Development orchestration, RAG pipeline |
| rugs-rl-bot | RL training, ML models |
| REPLAYER | Legacy production system |

---

## Security Considerations

1. **Chrome Profile Isolation:** Use dedicated `rugs_bot` profile, not default Chrome
2. **Wallet Access:** Profile has Phantom wallet connected - protect access
3. **Data Storage:** Parquet files contain trading history - secure appropriately
4. **WebSocket Exposure:** Foundation Service only binds to localhost by default

---

*Last updated: 2026-01-17*
