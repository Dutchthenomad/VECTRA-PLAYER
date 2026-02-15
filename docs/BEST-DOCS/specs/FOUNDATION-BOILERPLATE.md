# Foundation Service Boilerplate

**Version:** 1.0.0
**Date:** 2026-01-18
**Status:** Production Ready

---

## Overview

The Foundation Service provides a unified WebSocket feed for rugs.fun game events. It normalizes raw Socket.IO events from the game into a consistent format for subscribers.

## Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| WebSocket Feed | `ws://localhost:9000/feed` | Event stream |
| Monitoring UI | `http://localhost:9001` | Dashboard |
| Artifacts | `http://localhost:9001/artifacts/` | HTML artifacts |

## Starting the Service

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src
python -m foundation.launcher
```

The launcher will:
1. Start WebSocket broadcaster on port 9000
2. Start HTTP server on port 9001
3. Launch Chrome with `rugs_bot` profile
4. Navigate to rugs.fun
5. Begin intercepting and broadcasting events

---

## Event Types

### Normalized Event Format

Every event follows this structure:

```typescript
interface NormalizedEvent {
  type: string;      // Event type (see mapping below)
  ts: number;        // Unix timestamp (milliseconds)
  gameId: string;    // Current game ID
  seq: number;       // Sequence number (monotonic)
  data: object;      // Event-specific payload
}
```

### Event Type Mapping

| rugs.fun Event | Foundation Type | Description |
|----------------|-----------------|-------------|
| `gameStateUpdate` | `game.tick` | Price/tick stream (~50ms intervals) |
| `playerUpdate` | `player.state` | Balance/position changes |
| `usernameStatus` | `connection.authenticated` | Auth confirmation |
| `standard/newTrade` | `player.trade` | Trade broadcasts |
| `currentSidebet` | `sidebet.placed` | Sidebet placed |
| `currentSidebetResult` | `sidebet.result` | Sidebet outcome |
| `playerLeaderboardPosition` | `player.leaderboard` | Leaderboard position |
| (unknown) | `raw.<eventName>` | Passthrough for unmapped events |

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

## Minimal Client Example

### Python

```python
import asyncio
import json
import websockets

async def subscribe():
    uri = "ws://localhost:9000/feed"
    async with websockets.connect(uri) as ws:
        print("Connected to Foundation feed")
        async for message in ws:
            event = json.loads(message)
            handle_event(event)

def handle_event(event: dict):
    event_type = event["type"]
    data = event["data"]

    if event_type == "game.tick":
        print(f"Price: {data['price']:.4f} | Phase: {data['phase']}")
    elif event_type == "player.state":
        print(f"Cash: {data['cash']:.4f} | Position: {data['positionQty']}")
    elif event_type == "connection.authenticated":
        print(f"Authenticated as: {data['username']}")

asyncio.run(subscribe())
```

### JavaScript

```javascript
const ws = new WebSocket('ws://localhost:9000/feed');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'game.tick':
      console.log(`Price: ${msg.data.price} | Phase: ${msg.data.phase}`);
      break;
    case 'player.state':
      console.log(`Cash: ${msg.data.cash} | Position: ${msg.data.positionQty}`);
      break;
    case 'connection.authenticated':
      console.log(`Authenticated as: ${msg.data.username}`);
      break;
  }
};

ws.onopen = () => console.log('Connected to Foundation feed');
ws.onerror = (err) => console.error('WebSocket error:', err);
ws.onclose = () => console.log('Disconnected');
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

## Ping/Pong (Optional)

Clients can send ping messages for keepalive:

```json
// Client -> Server
{"action": "ping", "ts": 1704067200000}

// Server -> Client
{"type": "pong", "ts": 1704067200000}
```

---

## HTML Artifacts

The Foundation HTTP server serves HTML artifacts at `http://localhost:9001/artifacts/`.

To use artifacts that consume the WebSocket feed, place HTML files in:
```
/home/devops/Desktop/VECTRA-PLAYER/src/artifacts/
```

Example artifact that displays live price:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Live Price</title>
</head>
<body>
  <h1>Price: <span id="price">-</span></h1>
  <script>
    const ws = new WebSocket('ws://localhost:9000/feed');
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'game.tick') {
        document.getElementById('price').textContent = msg.data.price.toFixed(4);
      }
    };
  </script>
</body>
</html>
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

*Created: 2026-01-18 | Foundation Service v1.0.0*
