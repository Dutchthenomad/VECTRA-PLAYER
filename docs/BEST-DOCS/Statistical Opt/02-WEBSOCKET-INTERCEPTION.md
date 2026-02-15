# 02 - WebSocket Interception

## Purpose

Capture real-time game data from rugs.fun WebSocket connection for:
1. Live game state monitoring (tick, price, phase)
2. Player position tracking
3. Event recording for offline analysis
4. Training data generation for ML models

## Dependencies

```python
# From CDP integration
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor

# For direct WebSocket connection (alternative)
from sources.websocket_feed import WebSocketFeed
```

## Architecture

### Two Interception Methods

```
Method 1: CDP Interception (Primary)
┌──────────────────────────────────────────────────────┐
│  Chrome Browser                                       │
│  ┌────────────────┐    ┌────────────────────────┐   │
│  │  rugs.fun Tab  │◄──▶│  Socket.IO WebSocket   │   │
│  └────────────────┘    └──────────┬─────────────┘   │
│                                   │                  │
│  ┌────────────────────────────────▼─────────────┐   │
│  │            CDP Network Domain                 │   │
│  │  - Network.webSocketCreated                  │   │
│  │  - Network.webSocketFrameReceived            │   │
│  │  - Network.webSocketFrameSent                │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │ CDPWebSocketInterceptor │
              └──────────────────────┘

Method 2: Direct WebSocket (Fallback)
┌────────────────────────────────────┐
│  Python WebSocketFeed              │
│  wss://rugs.fun/socket.io/...     │
└───────────────┬────────────────────┘
                │
                ▼
        ┌───────────────┐
        │  EventBus     │
        └───────────────┘
```

## Key Patterns

### 1. Socket.IO Frame Parsing

rugs.fun uses Socket.IO which adds prefixes to WebSocket frames:

```python
def parse_socketio_frame(payload: str) -> dict | None:
    """
    Parse Socket.IO frame format.

    Frame types:
        "0"  - Connect
        "1"  - Disconnect
        "2"  - Event (ping)
        "3"  - Ack (pong)
        "4"  - Error
        "42" - Message (what we want)
    """
    if not payload.startswith("42"):
        return None  # Not a message frame

    # Strip "42" prefix and parse JSON
    json_str = payload[2:]

    try:
        data = json.loads(json_str)
        # Format: [event_name, event_data]
        return {
            "event": data[0],
            "data": data[1] if len(data) > 1 else {}
        }
    except json.JSONDecodeError:
        return None
```

### 2. CDP Event Handler

```python
class CDPWebSocketInterceptor:
    def __init__(self):
        self._session = None
        self._ws_url: str | None = None
        self.on_event: Callable | None = None

    async def connect(self, cdp_session) -> bool:
        """Connect and start interception"""
        self._session = cdp_session

        # Enable Network domain
        await self._session.send("Network.enable")

        # Register WebSocket handlers
        self._session.on("Network.webSocketCreated", self._on_ws_created)
        self._session.on("Network.webSocketFrameReceived", self._on_frame_received)
        self._session.on("Network.webSocketClosed", self._on_ws_closed)

        return True

    def _on_ws_created(self, params: dict):
        """Track WebSocket creation"""
        url = params.get("url", "")
        if "rugs.fun" in url or "socket.io" in url:
            self._ws_url = url
            logger.info(f"WebSocket created: {url[:50]}...")

    def _on_frame_received(self, params: dict):
        """Process incoming WebSocket frame"""
        response = params.get("response", {})
        payload = response.get("payloadData", "")

        if not payload:
            return

        # Parse Socket.IO frame
        parsed = parse_socketio_frame(payload)
        if parsed and self.on_event:
            self.on_event({
                **parsed,
                "source": "cdp",
                "timestamp": time.time()
            })
```

### 3. Direct WebSocket Feed

Alternative when CDP is unavailable:

```python
# src/sources/websocket_feed.py

class WebSocketFeed:
    """Direct WebSocket connection to rugs.fun"""

    RUGS_WS_URL = "wss://rugs.fun/socket.io/?EIO=4&transport=websocket"

    def __init__(self, log_level: str = "INFO"):
        self._callbacks: dict[str, list] = {}
        self._connected = False

    def on(self, event: str, callback: Callable):
        """Register event callback"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def connect(self):
        """Connect to WebSocket (blocking)"""
        import socketio

        self._sio = socketio.Client()

        @self._sio.on("gameStateUpdate")
        def on_game_state(data):
            self._emit("signal", GameSignal.from_dict(data))

        @self._sio.on("connect")
        def on_connect():
            self._connected = True
            self._emit("connected", {})

        self._sio.connect(self.RUGS_WS_URL)

    def _emit(self, event: str, data):
        """Emit to registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
```

### 4. Event Source Manager

Manages switching between CDP and direct WebSocket:

```python
class EventSourceManager:
    """Manages event source priority and switching"""

    def __init__(self):
        self._cdp_available = False
        self._ws_available = False
        self._current_source = "none"

    def set_cdp_available(self, available: bool):
        self._cdp_available = available
        self.switch_to_best_source()

    def switch_to_best_source(self):
        """Select best available source"""
        if self._cdp_available:
            self._current_source = "cdp"
            logger.info("Using CDP for event interception")
        elif self._ws_available:
            self._current_source = "websocket"
            logger.info("Using direct WebSocket")
        else:
            self._current_source = "none"
            logger.warning("No event source available")
```

## Event Types

### gameStateUpdate (Primary)

```python
{
    "event": "gameStateUpdate",
    "data": {
        "gameId": "abc123...",
        "tickCount": 150,
        "price": 2.45,
        "active": True,
        "rugged": False,
        "cooldownTimer": 0,
        "allowPreRoundBuys": False,
        "tradeCount": 42,
        "gameHistory": [...],  # 10-game rolling window
        "leaderboard": [...]
    }
}
```

### playerUpdate

```python
{
    "event": "playerUpdate",
    "data": {
        "cash": 0.5123,
        "positionQty": 100,
        "avgCost": 1.25,
        "cumulativePnL": 0.0523,
        "totalInvested": 0.125
    }
}
```

### usernameStatus

```python
{
    "event": "usernameStatus",
    "data": {
        "id": "player_uuid",
        "username": "player_name",
        "hasUsername": True
    }
}
```

### standard/newTrade

```python
{
    "event": "standard/newTrade",
    "data": {
        "username": "trader_name",
        "type": "buy",  # or "sell"
        "qty": 50,
        "price": 2.45,
        "playerId": "uuid"
    }
}
```

### currentSidebet / currentSidebetResult

```python
# Sidebet placed
{
    "event": "currentSidebet",
    "data": {
        "betAmount": 0.01,
        "entryTick": 200,
        "endTick": 240
    }
}

# Sidebet result
{
    "event": "currentSidebetResult",
    "data": {
        "won": True,
        "payout": 0.05
    }
}
```

## Integration Points

### With EventBus

```python
# All WebSocket events flow through EventBus
def on_cdp_event(event):
    event_bus.publish(Events.WS_RAW_EVENT, event)

interceptor.on_event = on_cdp_event
```

### With EventStore (Persistence)

```python
# EventStoreService subscribes to WS_RAW_EVENT
def _on_ws_raw_event(self, wrapped: dict):
    data = self._unwrap_event_payload(wrapped)

    envelope = EventEnvelope.from_ws_event(
        event_name=data.get("event"),
        data=data.get("data"),
        source=EventSource.CDP,
        session_id=self._session_id,
        seq=self._next_seq()
    )

    self._writer.write(envelope)
```

### With BrowserService (UI Updates)

```python
# BrowserService forwards to SocketIO
def _on_ws_event(self, event: dict):
    if event.get("event") == "gameStateUpdate":
        self._handle_game_state(event.get("data", {}))

        # Forward to frontend
        if self._socketio:
            self._socketio.emit("game_state", {...})
```

## Configuration

### WebSocket URLs

```python
# rugs.fun Socket.IO endpoint
RUGS_WS_URL = "wss://rugs.fun/socket.io/?EIO=4&transport=websocket"

# EIO=4 indicates Socket.IO v4 protocol
# transport=websocket bypasses long-polling
```

### Reconnection Settings

```python
# Direct WebSocket reconnection
RECONNECT_DELAY = 1.0  # Initial delay
RECONNECT_MAX_DELAY = 30.0  # Max backoff
RECONNECT_MAX_ATTEMPTS = 10
```

## Gotchas

1. **Socket.IO Protocol**: Frames have prefixes ("42" for messages). Must parse correctly.

2. **gameHistory Deduplication**: gameHistory is 10-game rolling window. Same game appears ~10 times. Deduplicate by gameId.

3. **CDP vs Direct**: CDP intercepts browser's WebSocket (authenticated). Direct WebSocket gets public events only.

4. **Pre-existing WebSocket**: If Chrome was already connected before CDP setup, must force Socket.IO reconnect.

5. **Binary Frames**: Some frames may be binary (for efficiency). Skip or decode appropriately.

6. **Heartbeat**: Socket.IO sends ping/pong ("2"/"3"). Don't process as events.

7. **Event Burst**: gameStateUpdate fires every ~250ms during active game. High-frequency handling required.
