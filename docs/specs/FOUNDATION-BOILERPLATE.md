# Foundation Boilerplate Framework Specification

**Version:** 1.0.0
**Date:** 2026-01-18
**Status:** ENFORCED

---

## Overview

This specification defines the **mandatory** framework for all Foundation Service subscribers. Every HTML artifact and Python subscriber **MUST** follow these rules.

**Why?** To eliminate:
- 20+ scattered HTML files with different patterns
- Repeated WebSocket connection code
- Inconsistent styling and error handling
- Token waste from agents recreating existing infrastructure

---

## RULES (Not Guidelines)

### Rule 1: HTML Artifacts Location

| Allowed | NOT Allowed |
|---------|-------------|
| `src/artifacts/tools/<name>/` | `src/rugs_recordings/` |
| `src/artifacts/templates/` | `src/recording_ui/templates/` |
| | Root directory |
| | Any other location |

**IMMUTABLE directories (DO NOT MODIFY):**
- `src/artifacts/shared/` - Standard WebSocket client and styles
- `src/artifacts/templates/` - Reference templates

### Rule 2: HTML Must Import Shared Resources

Every HTML file **MUST** include:

```html
<!-- REQUIRED: Foundation WebSocket Client -->
<script src="../../shared/foundation-ws-client.js"></script>

<!-- REQUIRED: Standard Styles -->
<link rel="stylesheet" href="../../shared/vectra-styles.css">
```

### Rule 3: NO Custom WebSocket Code

**PROHIBITED:**
```javascript
// DO NOT DO THIS
const ws = new WebSocket('ws://localhost:9000/feed');
ws.onmessage = (e) => { ... };
```

**REQUIRED:**
```javascript
// USE THIS
const client = new FoundationWSClient();
client.on('game.tick', (event) => { ... });
client.connect();
```

### Rule 4: Python Subscribers Inherit BaseSubscriber

All Python subscribers **MUST** inherit from `BaseSubscriber`:

```python
from foundation.subscriber import BaseSubscriber
from foundation.events import GameTickEvent, PlayerStateEvent

class MySubscriber(BaseSubscriber):
    def on_game_tick(self, event: GameTickEvent) -> None:
        # Handle game tick
        pass

    def on_player_state(self, event: PlayerStateEvent) -> None:
        # Handle player state
        pass

    def on_connection_change(self, connected: bool) -> None:
        # Handle connection changes
        pass
```

### Rule 5: Python Subscribers Location

| Allowed | NOT Allowed |
|---------|-------------|
| `src/subscribers/<name>/` | Root directory |
| | Random package locations |

### Rule 6: NO Direct WebSocket in Python

**PROHIBITED:**
```python
# DO NOT DO THIS
import websockets
ws = await websockets.connect('ws://localhost:9000/feed')
```

**REQUIRED:**
```python
# USE THIS
from foundation.client import FoundationClient

client = FoundationClient()
await client.connect()
```

---

## Directory Structure

### HTML Artifacts

```
src/artifacts/
├── shared/                      # IMMUTABLE - DO NOT MODIFY
│   ├── foundation-ws-client.js  # Standard WebSocket client
│   └── vectra-styles.css        # Standard styles
├── templates/                   # IMMUTABLE - DO NOT MODIFY
│   ├── artifact-template.html   # Reference HTML template
│   └── artifact-template.js     # Reference JS template
├── tools/                       # NEW ARTIFACTS GO HERE
│   ├── seed-bruteforce/
│   │   ├── index.html          # Must import shared resources
│   │   ├── main.js             # Must use FoundationWSClient
│   │   └── README.md           # REQUIRED
│   └── <your-new-tool>/        # Create your tools here
│       ├── index.html
│       ├── main.js
│       └── README.md
└── orchestrator/               # Tab manager (existing)
```

### Python Subscribers

```
src/
├── foundation/                  # Foundation Service core
│   ├── client.py               # FoundationClient class
│   ├── events.py               # Typed event dataclasses
│   └── subscriber.py           # BaseSubscriber abstract class
└── subscribers/                # NEW SUBSCRIBERS GO HERE
    ├── __init__.py
    ├── example/
    │   └── subscriber.py       # Example implementation
    └── <your-subscriber>/
        └── subscriber.py
```

---

## Python API Reference

### FoundationClient

```python
from foundation.client import FoundationClient

client = FoundationClient(
    url="ws://localhost:9000/feed",  # Optional: custom URL
    reconnect_delay=1.0,              # Initial reconnect delay
    max_reconnect_delay=30.0,         # Max reconnect delay
    reconnect_multiplier=1.5,         # Backoff multiplier
)

# Connect (async)
await client.connect()

# Subscribe to events
unsubscribe = client.on('game.tick', handle_tick)
unsubscribe()  # Remove listener

# Check connection
client.is_connected()

# Get metrics
metrics = client.get_metrics()

# Disconnect
await client.disconnect()
```

### Event Types

| Event Type | Python Class | Key Fields |
|------------|--------------|------------|
| `game.tick` | `GameTickEvent` | `price`, `tick_count`, `phase`, `active`, `rugged` |
| `player.state` | `PlayerStateEvent` | `cash`, `position_qty`, `avg_cost`, `cumulative_pnl` |
| `connection.authenticated` | `ConnectionAuthenticatedEvent` | `username`, `player_id` |
| `player.trade` | `PlayerTradeEvent` | `username`, `trade_type`, `qty`, `price` |
| `sidebet.placed` | `SidebetEvent` | `amount`, `prediction`, `target_tick` |
| `sidebet.result` | `SidebetResultEvent` | `won`, `payout` |

### BaseSubscriber

```python
from foundation.subscriber import BaseSubscriber

class MySubscriber(BaseSubscriber):
    # REQUIRED: Must implement these
    def on_game_tick(self, event: GameTickEvent) -> None: ...
    def on_player_state(self, event: PlayerStateEvent) -> None: ...
    def on_connection_change(self, connected: bool) -> None: ...

    # OPTIONAL: Override if needed
    def on_player_trade(self, event: PlayerTradeEvent) -> None: ...
    def on_sidebet_placed(self, event: SidebetEvent) -> None: ...
    def on_sidebet_result(self, event: SidebetResultEvent) -> None: ...
    def on_raw_event(self, event: dict) -> None: ...  # Unknown events
```

---

## JavaScript API Reference

### FoundationWSClient

```javascript
const client = new FoundationWSClient({
    url: 'ws://localhost:9000/feed',  // Optional
    reconnectDelay: 1000,              // ms
    maxReconnectDelay: 30000,          // ms
    reconnectMultiplier: 1.5,
});

// Connect
await client.connect();

// Subscribe to events
const unsubscribe = client.on('game.tick', (event) => {
    console.log(event.data.price);
});

// Wildcard listener (all events)
client.on('*', (event) => console.log(event));

// Check connection
client.isConnected();

// Get metrics
const metrics = client.getMetrics();

// Get buffered events (for late subscribers)
const recentTicks = client.getRecentEvents('game.tick');

// Disconnect
client.disconnect();
```

---

## Validation

### Before Merge

Run validation script on all new artifacts:

```bash
# Validate HTML tool
python scripts/validate_artifact.py src/artifacts/tools/my-tool/

# Validate Python subscriber
python scripts/validate_artifact.py src/subscribers/my_subscriber/subscriber.py
```

### Validation Checks

| Check | HTML | Python |
|-------|------|--------|
| Correct location | ✓ | ✓ |
| Imports shared resources | ✓ | - |
| No custom WebSocket | ✓ | ✓ |
| Inherits BaseSubscriber | - | ✓ |
| Has README.md | ✓ (tools) | - |

---

## Creating a New HTML Tool

1. **Create directory:**
   ```bash
   mkdir src/artifacts/tools/my-new-tool
   ```

2. **Copy template:**
   ```bash
   cp src/artifacts/templates/artifact-template.html src/artifacts/tools/my-new-tool/index.html
   cp src/artifacts/templates/artifact-template.js src/artifacts/tools/my-new-tool/main.js
   ```

3. **Create README:**
   ```bash
   echo "# My New Tool\n\nDescription here." > src/artifacts/tools/my-new-tool/README.md
   ```

4. **Implement your logic in `main.js`**

5. **Validate before commit:**
   ```bash
   python scripts/validate_artifact.py src/artifacts/tools/my-new-tool/
   ```

---

## Creating a New Python Subscriber

1. **Create directory:**
   ```bash
   mkdir -p src/subscribers/my-subscriber
   touch src/subscribers/my-subscriber/__init__.py
   ```

2. **Implement subscriber:**
   ```python
   # src/subscribers/my-subscriber/subscriber.py
   from foundation.subscriber import BaseSubscriber
   from foundation.events import GameTickEvent, PlayerStateEvent

   class MySubscriber(BaseSubscriber):
       def on_game_tick(self, event: GameTickEvent) -> None:
           print(f"Price: {event.price}")

       def on_player_state(self, event: PlayerStateEvent) -> None:
           print(f"Cash: {event.cash}")

       def on_connection_change(self, connected: bool) -> None:
           print(f"Connected: {connected}")
   ```

3. **Validate before commit:**
   ```bash
   python scripts/validate_artifact.py src/subscribers/my-subscriber/subscriber.py
   ```

---

## FAQ

### Why can't I use raw WebSocket?

The `FoundationWSClient` (JS) and `FoundationClient` (Python) provide:
- Automatic reconnection with exponential backoff
- Event buffering for late subscribers
- Latency metrics
- Consistent event typing
- Error handling

Rolling your own loses all of this.

### Can I modify shared/?

**NO.** The `src/artifacts/shared/` directory is IMMUTABLE. If you need changes:
1. Open an issue
2. Propose the change
3. Get approval
4. Modify via PR with tests

### What about existing Flask templates?

The existing `src/recording_ui/templates/` Flask templates are legacy. New dashboard features should use the Foundation framework instead.

### How do I handle unknown events?

Override `on_raw_event()` in your subscriber:

```python
def on_raw_event(self, event: dict) -> None:
    print(f"Unknown event: {event['type']}")
```

---

## Event Data Schemas

### game.tick

```typescript
interface GameTickData {
  active: boolean;           // Game is active
  rugged: boolean;           // Game ended (rug pulled)
  price: number;             // Current price (1.0 = starting)
  tickCount: number;         // Ticks since game start
  cooldownTimer: number;     // Cooldown ms remaining
  allowPreRoundBuys: boolean;// Pre-round buying allowed
  tradeCount: number;        // Total trades this game
  phase: string;             // COOLDOWN|PRESALE|ACTIVE|RUGGED
  gameHistory: object|null;  // Previous game results
  leaderboard: object[]|null;// Current leaderboard
}
```

### player.state

```typescript
interface PlayerStateData {
  cash: number;              // Available balance
  positionQty: number;       // Current position size
  avgCost: number;           // Average entry price
  cumulativePnL: number;     // Total profit/loss
  totalInvested: number;     // Total invested
}
```

### player.trade

```typescript
interface PlayerTradeData {
  username: string;          // Trader username
  type: "buy" | "sell";      // Trade direction
  qty: number;               // Trade quantity
  price: number;             // Execution price
  playerId: string;          // Trader ID
}
```

### connection.authenticated

```typescript
interface AuthData {
  player_id: string;         // Player ID
  username: string;          // Username
  hasUsername: boolean;      // Has set username
}
```

---

## Game Phases

The `game.tick` event includes a `phase` field:

| Phase | Condition | Description |
|-------|-----------|-------------|
| `COOLDOWN` | `cooldownTimer > 0` | Between games |
| `PRESALE` | `allowPreRoundBuys && !active` | Pre-round buying |
| `ACTIVE` | `active && !rugged` | Game in progress |
| `RUGGED` | `rugged` | Game ended (rug pulled) |

---

## Error Handling Pattern

```python
import asyncio
import websockets

RECONNECT_DELAY = 5  # seconds

async def resilient_subscribe():
    while True:
        try:
            async with websockets.connect("ws://localhost:9000/feed") as ws:
                print("Connected")
                async for message in ws:
                    handle_event(json.loads(message))
        except websockets.ConnectionClosed:
            print(f"Disconnected, reconnecting in {RECONNECT_DELAY}s...")
        except Exception as e:
            print(f"Error: {e}, reconnecting in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)
```

---

## Configuration

Environment variables for custom ports:

```bash
FOUNDATION_PORT=9000        # WebSocket broadcaster
FOUNDATION_HTTP_PORT=9001   # HTTP server
CDP_PORT=9222               # Chrome DevTools Protocol
FOUNDATION_HEADLESS=false   # Headless Chrome mode
```

---

## Related Files

| Component | Location |
|-----------|----------|
| Config | `src/foundation/config.py` |
| Normalizer | `src/foundation/normalizer.py` |
| Broadcaster | `src/foundation/broadcaster.py` |
| HTTP Server | `src/foundation/http_server.py` |
| Launcher | `src/foundation/launcher.py` |
| Service | `src/foundation/service.py` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-18 | Initial specification with merged framework rules and service documentation |
