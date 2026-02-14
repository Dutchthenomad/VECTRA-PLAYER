# Foundation System Design Session

## Mission

Design and implement a **bulletproof foundation system** for VECTRA-PLAYER that provides a single, reliable connection to the rugs.fun WebSocket feed with a clean protocol that any downstream system can easily subscribe to.

**This is the #1 priority.** Every recurring bug, integration headache, and wasted development time traces back to not having this foundation right.

---

## The Problem (Why We're Here)

### Current Pain Points

1. **Fragmented WebSocket handling** - Multiple places trying to connect to rugs.fun:
   - `src/sources/websocket_feed.py` - Direct Socket.IO client
   - `src/recording_ui/` - Flask-SocketIO trying to proxy events
   - CDP (Chrome DevTools Protocol) intercept for authenticated events
   - Each approach has different quirks, reconnection logic, and failure modes

2. **Hardcoded configuration nightmare** - Paths, ports, and settings scattered across:
   - `config.py` with hardcoded defaults
   - Flask routes with inline configuration
   - Service classes with their own path assumptions
   - No single source of truth

3. **No clear protocol** - Every new feature reinvents how to get game data:
   - Recording system subscribes one way
   - Backtest UI subscribes another way
   - Bot systems have their own connection
   - No documentation a future developer (or AI) can rely on

4. **Chrome profile chaos** - The `rugs_bot` profile is critical for authenticated WebSocket access, but:
   - Multiple scripts try to launch Chrome differently
   - CDP connection logic is duplicated
   - Profile path handling is inconsistent

### What We Keep Breaking

Every time we add a feature, we break something because there's no stable foundation:
- Recording toggle stops working
- Live feed drops during backtest
- Bot can't get game state
- Chrome launches with wrong profile

---

## The Solution (What We're Building)

### Core Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FOUNDATION SERVICE                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           Chrome Manager (rugs_bot profile)                  │   │
│  │  - Launches Chrome with correct profile                      │   │
│  │  - Manages CDP connection                                    │   │
│  │  - Handles WebSocket authentication via browser session      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           WebSocket Feed (Socket.IO to rugs.fun)             │   │
│  │  - Single connection to backend.rugs.fun                     │   │
│  │  - Automatic reconnection                                    │   │
│  │  - Event normalization                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           Event Broadcaster (ZeroMQ / Redis / WebSocket)     │   │
│  │  - Pub/sub for all downstream systems                        │   │
│  │  - Guaranteed message delivery                               │   │
│  │  - Multiple transport options                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Recording   │    │   Backtest UI    │    │   Trading Bot    │
│   Service    │    │   (WebSocket)    │    │    (Python)      │
└──────────────┘    └──────────────────┘    └──────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  EventStore  │    │  TypeScript UI   │    │  Strategy Engine │
│  (Parquet)   │    │  (Future)        │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

### Design Requirements

1. **Single Point of Connection**
   - ONE process connects to rugs.fun
   - All other systems subscribe to this process
   - If it dies, everything knows immediately

2. **Protocol Documentation**
   - Every event type fully documented
   - Example payloads for each event
   - Subscription commands clearly defined
   - Error handling patterns specified

3. **Environment-Based Configuration**
   - All paths from environment variables
   - Sensible defaults in one place
   - No hardcoded strings in business logic

4. **Containerization Option**
   - Docker Compose for full stack
   - Can run standalone for development
   - Same behavior in both modes

5. **Health Monitoring**
   - Connection status endpoint
   - Latency metrics
   - Reconnection count
   - Last event timestamp

---

## Key Decisions to Make

### 1. Broadcast Protocol

**Options:**
- **ZeroMQ PUB/SUB** - Fast, simple, no broker needed
- **Redis Pub/Sub** - Already common, persistence option
- **WebSocket Server** - Native browser support
- **Unix Domain Socket** - Fastest for local processes
- **Combination** - Internal ZeroMQ + WebSocket for browsers

**Consider:**
- Browser-based UI needs WebSocket
- Python bots can use anything
- Recording needs every event, no drops
- Latency requirements for trading

### 2. Chrome Management

**Options:**
- **Subprocess management** - Launch Chrome via Python
- **Docker sidecar** - Chrome in container with VNC
- **Playwright/Puppeteer** - Managed browser automation
- **Existing CDP approach** - Keep current, just isolate

**Consider:**
- The `rugs_bot` profile must be used
- CDP is needed for authenticated WebSocket
- Stability across restarts
- Headless vs headed for debugging

### 3. Service Orchestration

**Options:**
- **Single Python process** - Simple, but single point of failure
- **Docker Compose** - Container per service, orchestrated
- **systemd services** - Native Linux, proven
- **Supervisor** - Python-native process management

**Consider:**
- Development workflow (hot reload)
- Production stability
- Log aggregation
- Restart policies

---

## Protocol Specification (Draft)

### Event Types

| Event | Source | Description |
|-------|--------|-------------|
| `game.tick` | gameStateUpdate | Price/tick stream during active game |
| `game.start` | gameStateUpdate | New game begins (phase change) |
| `game.end` | gameStateUpdate | Game ends (rug or completion) |
| `player.update` | playerUpdate | Our balance/position changed |
| `player.trade` | newTrade | Another player traded |
| `connection.status` | Internal | Connected/disconnected/reconnecting |
| `error` | Internal | Something went wrong |

### Message Format

```json
{
  "type": "game.tick",
  "timestamp": 1736956800000,
  "gameId": "abc123",
  "data": {
    "tickCount": 42,
    "price": "1.234567",
    "active": true,
    "rugged": false,
    "phase": "ACTIVE"
  }
}
```

### Subscription Commands

```json
{"action": "subscribe", "channels": ["game.*", "player.update"]}
{"action": "unsubscribe", "channels": ["player.trade"]}
{"action": "ping"}
```

---

## Existing Code to Preserve

### Keep and Refactor
- `src/sources/websocket_feed.py` - Core Socket.IO client (wrap, don't replace)
- `src/services/event_bus.py` - Internal pub/sub (use as internal event dispatch)
- `src/services/event_store/` - Parquet persistence (subscriber to new system)
- `src/models/` - Data models (extend for new events)

### Deprecate
- `src/recording_ui/` - Flask UI (move to `_archived/`)
- Scattered configuration in route files
- Multiple CDP connection attempts

---

## Development Approach

### Use Git Worktree

```bash
# Create isolated workspace for this work
cd /home/devops/Desktop/VECTRA-PLAYER
git worktree add ../VECTRA-FOUNDATION feature/foundation-system

# Work in isolation
cd ../VECTRA-FOUNDATION
```

### TDD from the Start

1. Write tests for the protocol
2. Implement minimal working system
3. Add subscribers one at a time
4. Each subscriber is a separate PR

### Phases

**Phase 0: Design**
- Finalize protocol specification
- Choose broadcast mechanism
- Design configuration schema
- Document everything

**Phase 1: Core Service**
- Chrome manager (profile launcher)
- WebSocket feed wrapper
- Event broadcaster
- Health endpoint

**Phase 2: First Subscriber (Recording)**
- EventStore subscribes to broadcaster
- Proves the pattern works
- Full test coverage

**Phase 3: UI Subscriber**
- WebSocket endpoint for browsers
- Simple HTML test page
- Validates browser integration

**Phase 4: Bot Integration**
- Python client library
- Trading bot subscribes
- Execution commands (buy/sell)

---

## Success Criteria

- [ ] Single command starts entire system: `./start.sh`
- [ ] Any new subscriber can connect in <10 lines of code
- [ ] Protocol documented so any AI assistant can use it correctly
- [ ] Zero hardcoded paths in application code
- [ ] Automatic reconnection with no data loss
- [ ] Health endpoint shows system status
- [ ] Works identically in Docker and standalone
- [ ] All existing functionality preserved

---

## Reference Files

### Chrome Profile
```
~/.gamebot/chrome_profiles/rugs_bot/
```

### WebSocket Events Spec
```
docs/rag/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md
```

### Current Architecture
```
CLAUDE.md
```

### Previous Plan (partial, for reference)
```
docs/plans/2026-01-15-typescript-frontend-api-redesign.md
```

---

## Starting Point

Begin by:

1. **Invoking `/worktree`** to create isolated workspace
2. **Brainstorming broadcast protocol** - What's the right choice for our use case?
3. **Designing configuration schema** - Pydantic Settings with all options
4. **Writing protocol specification** - Complete, unambiguous, testable

Do NOT write implementation code until the design is approved.

---

*Created: January 15, 2026*
*Goal: Bulletproof foundation that never breaks again*
