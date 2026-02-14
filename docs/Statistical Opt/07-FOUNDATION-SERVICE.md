# 07 - Foundation Service

## Purpose

The Foundation Service provides a unified WebSocket broadcaster for:
1. Normalizing rugs.fun events to standard types
2. Broadcasting to HTML artifacts and external consumers
3. Managing Chrome browser lifecycle
4. Providing monitoring UI

## Dependencies

```python
# Foundation modules
from foundation.normalizer import EventNormalizer
from foundation.broadcaster import WebSocketBroadcaster
from foundation.http_server import MonitoringServer
from foundation.launcher import launch_foundation
from foundation.config import get_config
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Foundation Service                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  Chrome Browser │                                                         │
│  │  (rugs.fun)     │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                   │
│           ▼                                                                   │
│  ┌─────────────────────┐      ┌─────────────────────────────────────┐       │
│  │ CDP WS Interceptor  │─────▶│         Event Normalizer            │       │
│  └─────────────────────┘      │                                     │       │
│                               │  rugs.fun Event → Foundation Type   │       │
│                               │                                     │       │
│                               │  gameStateUpdate → game.tick        │       │
│                               │  playerUpdate → player.state        │       │
│                               │  usernameStatus → connection.auth   │       │
│                               │  newTrade → player.trade            │       │
│                               └───────────────┬─────────────────────┘       │
│                                               │                              │
│                                               ▼                              │
│                               ┌─────────────────────────────────────┐       │
│                               │      WebSocket Broadcaster          │       │
│                               │      ws://localhost:9000/feed       │       │
│                               └───────────────┬─────────────────────┘       │
│                                               │                              │
│               ┌───────────────┬───────────────┼───────────────┐             │
│               ▼               ▼               ▼               ▼             │
│        ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐       │
│        │  Artifact │   │  Artifact │   │ Dashboard │   │  External │       │
│        │  (HTML)   │   │  (HTML)   │   │   UI      │   │  Client   │       │
│        └───────────┘   └───────────┘   └───────────┘   └───────────┘       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Monitoring Server (Port 9001)                     │   │
│  │  - Connection status                                                 │   │
│  │  - Event throughput                                                  │   │
│  │  - Client count                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Event Normalization

```python
# src/foundation/normalizer.py

from dataclasses import dataclass
from typing import Any
from enum import Enum

class FoundationEventType(Enum):
    """Normalized event types"""
    GAME_TICK = "game.tick"
    GAME_END = "game.end"
    PLAYER_STATE = "player.state"
    PLAYER_TRADE = "player.trade"
    CONNECTION_AUTHENTICATED = "connection.authenticated"
    SIDEBET_PLACED = "sidebet.placed"
    SIDEBET_RESULT = "sidebet.result"
    SYSTEM_ERROR = "system.error"

@dataclass
class FoundationEvent:
    """Normalized event structure"""
    type: str
    timestamp: float
    game_id: str | None
    data: dict

class EventNormalizer:
    """Transform rugs.fun events to Foundation types"""

    # Event mapping table
    EVENT_MAP = {
        "gameStateUpdate": FoundationEventType.GAME_TICK,
        "playerUpdate": FoundationEventType.PLAYER_STATE,
        "usernameStatus": FoundationEventType.CONNECTION_AUTHENTICATED,
        "standard/newTrade": FoundationEventType.PLAYER_TRADE,
        "currentSidebet": FoundationEventType.SIDEBET_PLACED,
        "currentSidebetResult": FoundationEventType.SIDEBET_RESULT,
    }

    def normalize(self, raw_event: dict) -> FoundationEvent | None:
        """
        Transform raw rugs.fun event to Foundation format.

        Args:
            raw_event: Raw event from WebSocket
                {"event": "gameStateUpdate", "data": {...}}

        Returns:
            FoundationEvent or None if unmappable
        """
        event_name = raw_event.get("event")
        event_data = raw_event.get("data", {})

        if event_name not in self.EVENT_MAP:
            return None

        event_type = self.EVENT_MAP[event_name]

        # Extract common fields
        game_id = event_data.get("gameId")
        timestamp = raw_event.get("timestamp", time.time())

        # Transform data based on event type
        normalized_data = self._transform_data(event_type, event_data)

        return FoundationEvent(
            type=event_type.value,
            timestamp=timestamp,
            game_id=game_id,
            data=normalized_data
        )

    def _transform_data(self, event_type: FoundationEventType,
                        raw_data: dict) -> dict:
        """Transform event-specific data"""
        if event_type == FoundationEventType.GAME_TICK:
            return {
                "tick": raw_data.get("tickCount", 0),
                "price": float(raw_data.get("price", 1.0)),
                "active": raw_data.get("active", False),
                "rugged": raw_data.get("rugged", False),
                "phase": self._detect_phase(raw_data),
            }
        elif event_type == FoundationEventType.PLAYER_STATE:
            return {
                "cash": float(raw_data.get("cash", 0)),
                "position_qty": float(raw_data.get("positionQty", 0)),
                "avg_cost": float(raw_data.get("avgCost", 0)),
                "pnl": float(raw_data.get("cumulativePnL", 0)),
            }
        # ... more transformations
        return raw_data
```

### 2. WebSocket Broadcaster

```python
# src/foundation/broadcaster.py

import asyncio
import websockets
from collections import defaultdict

class WebSocketBroadcaster:
    """Broadcast normalized events to connected clients"""

    def __init__(self, port: int = 9000):
        self.port = port
        self.clients: set[websockets.WebSocketServerProtocol] = set()
        self._server = None

    async def start(self):
        """Start WebSocket server"""
        self._server = await websockets.serve(
            self._handle_client,
            "0.0.0.0",
            self.port,
            ping_interval=20,
            ping_timeout=20,
        )
        logger.info(f"WebSocket broadcaster started on ws://localhost:{self.port}/feed")

    async def _handle_client(self, websocket, path):
        """Handle new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected ({len(self.clients)} total)")

        try:
            async for message in websocket:
                # Handle client messages (subscription requests, etc.)
                await self._handle_message(websocket, message)
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected ({len(self.clients)} total)")

    async def broadcast(self, event: FoundationEvent):
        """Broadcast event to all connected clients"""
        if not self.clients:
            return

        message = json.dumps({
            "type": event.type,
            "timestamp": event.timestamp,
            "game_id": event.game_id,
            "data": event.data,
        })

        # Broadcast concurrently
        await asyncio.gather(
            *[self._send_safe(client, message) for client in self.clients],
            return_exceptions=True
        )

    async def _send_safe(self, client, message):
        """Send with error handling"""
        try:
            await client.send(message)
        except websockets.ConnectionClosed:
            self.clients.discard(client)
```

### 3. HTTP Monitoring Server

```python
# src/foundation/http_server.py

from aiohttp import web

class MonitoringServer:
    """HTTP server for monitoring and status"""

    def __init__(self, port: int = 9001):
        self.port = port
        self._stats = {
            "events_processed": 0,
            "clients_connected": 0,
            "uptime_seconds": 0,
        }

    async def start(self):
        """Start HTTP server"""
        app = web.Application()
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/api/status", self._handle_status)
        app.router.add_static("/static", "foundation/static")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()

        logger.info(f"Monitoring server at http://localhost:{self.port}")

    async def _handle_index(self, request):
        """Serve monitoring UI"""
        return web.FileResponse("foundation/static/monitor.html")

    async def _handle_status(self, request):
        """Return JSON status"""
        return web.json_response(self._stats)

    def update_stats(self, **kwargs):
        """Update statistics"""
        self._stats.update(kwargs)
```

### 4. Service Launcher

```python
# src/foundation/launcher.py

import asyncio
from foundation.config import get_config
from foundation.normalizer import EventNormalizer
from foundation.broadcaster import WebSocketBroadcaster
from browser.bridge import get_browser_bridge

async def launch_foundation():
    """Launch all Foundation services"""
    config = get_config()

    # Initialize components
    normalizer = EventNormalizer()
    broadcaster = WebSocketBroadcaster(port=config.ws_port)
    monitoring = MonitoringServer(port=config.http_port)

    # Start servers
    await broadcaster.start()
    await monitoring.start()

    # Connect to browser
    bridge = get_browser_bridge()
    bridge.connect()

    # Hook CDP events to broadcaster
    def on_raw_event(event):
        normalized = normalizer.normalize(event)
        if normalized:
            asyncio.create_task(broadcaster.broadcast(normalized))
            monitoring.update_stats(events_processed=monitoring._stats["events_processed"] + 1)

    bridge.on_event = on_raw_event

    # Update client count
    original_add = broadcaster.clients.add
    def tracked_add(client):
        original_add(client)
        monitoring.update_stats(clients_connected=len(broadcaster.clients))
    broadcaster.clients.add = tracked_add

    logger.info("Foundation Service running")

    # Keep running
    while True:
        await asyncio.sleep(1)

def main():
    """Entry point"""
    asyncio.run(launch_foundation())

if __name__ == "__main__":
    main()
```

### 5. Configuration

```python
# src/foundation/config.py

from dataclasses import dataclass
import os

@dataclass
class FoundationConfig:
    """Foundation Service configuration"""
    ws_port: int = 9000          # WebSocket broadcaster
    http_port: int = 9001        # Monitoring UI
    cdp_port: int = 9222         # Chrome DevTools
    headless: bool = False       # Headless Chrome
    chrome_profile: str = "rugs_bot"

def get_config() -> FoundationConfig:
    """Load config from environment"""
    return FoundationConfig(
        ws_port=int(os.getenv("FOUNDATION_PORT", 9000)),
        http_port=int(os.getenv("FOUNDATION_HTTP_PORT", 9001)),
        cdp_port=int(os.getenv("CDP_PORT", 9222)),
        headless=os.getenv("FOUNDATION_HEADLESS", "false").lower() == "true",
        chrome_profile=os.getenv("CHROME_PROFILE", "rugs_bot"),
    )
```

## Event Type Mapping

| rugs.fun Event | Foundation Type | Key Fields |
|----------------|-----------------|------------|
| `gameStateUpdate` | `game.tick` | tick, price, active, rugged |
| `playerUpdate` | `player.state` | cash, position_qty, avg_cost |
| `usernameStatus` | `connection.authenticated` | player_id, username |
| `standard/newTrade` | `player.trade` | username, type, qty, price |
| `currentSidebet` | `sidebet.placed` | bet_amount, entry_tick |
| `currentSidebetResult` | `sidebet.result` | won, payout |

## Integration Points

### With BrowserBridge

```python
# Hook CDP events
bridge = get_browser_bridge()
bridge.on_event = lambda evt: asyncio.create_task(
    broadcaster.broadcast(normalizer.normalize(evt))
)
```

### With HTML Artifacts

```javascript
// In HTML artifact
const ws = new WebSocket('ws://localhost:9000/feed');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'game.tick':
            updateGameDisplay(data.data);
            break;
        case 'player.state':
            updatePlayerInfo(data.data);
            break;
    }
};
```

### With External Consumers

```python
# External Python client
import asyncio
import websockets
import json

async def consume_feed():
    async with websockets.connect("ws://localhost:9000/feed") as ws:
        async for message in ws:
            event = json.loads(message)
            print(f"[{event['type']}] {event['data']}")

asyncio.run(consume_feed())
```

## Configuration

### Environment Variables

```bash
FOUNDATION_PORT=9000        # WebSocket broadcaster
FOUNDATION_HTTP_PORT=9001   # Monitoring UI
CDP_PORT=9222               # Chrome DevTools
FOUNDATION_HEADLESS=false   # Headless mode
CHROME_PROFILE=rugs_bot     # Profile name
```

### Startup Command

```bash
python -m foundation.launcher
```

## Gotchas

1. **Port Conflicts**: Ensure ports 9000, 9001, 9222 are available.

2. **Chrome Profile**: Must use `rugs_bot` profile for Phantom wallet access.

3. **Event Flood**: gameStateUpdate fires every ~250ms. Handle high throughput.

4. **Async Context**: Broadcast from sync callback requires `asyncio.create_task()`.

5. **WebSocket Ping**: Configure ping_interval/ping_timeout to keep connections alive.

6. **Client Cleanup**: Remove disconnected clients from set to prevent memory leak.

7. **Startup Order**: Start broadcaster before connecting bridge to avoid dropped events.
