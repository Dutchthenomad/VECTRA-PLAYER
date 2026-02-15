# 01 - Browser CDP Integration

## Purpose

The Chrome DevTools Protocol (CDP) layer enables VECTRA-PLAYER to:
1. Connect to Chrome browser running rugs.fun
2. Intercept WebSocket traffic between browser and game server
3. Execute button clicks to place trades
4. Capture game state in real-time

## Dependencies

```python
# Core packages
playwright              # Browser automation via CDP
flask-socketio         # Real-time event forwarding

# Internal modules
from browser.bridge import BrowserBridge, get_browser_bridge
from browser.manager import CDPBrowserManager
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor
```

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        BrowserBridge                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐ │
│  │ UI Thread    │    │  Async Loop      │    │  CDP Manager    │ │
│  │ (Flask)      │───▶│  (Action Queue)  │───▶│  (Playwright)   │ │
│  └──────────────┘    └──────────────────┘    └────────┬────────┘ │
│                                                       │          │
│  ┌──────────────────────────────────────────────────┐│          │
│  │              CDP WebSocket Interceptor           ││          │
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────────┐ ││          │
│  │  │ Network │  │ WebSocket   │  │ Event       │ ││          │
│  │  │ Domain  │──│ Frame Parse │──│ Callback    │ ││          │
│  │  └─────────┘  └─────────────┘  └─────────────┘ ││          │
│  └──────────────────────────────────────────────────┘│          │
│                                                       │          │
│  ┌────────────────────────────────────────────────────▼────────┐ │
│  │                    Chrome Browser                           │ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │  rugs.fun Tab                                           ││ │
│  │  │  - Socket.IO WebSocket                                  ││ │
│  │  │  - Trading UI (BUY/SELL/SIDEBET buttons)               ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Chrome Profile Configuration

**Critical**: Must use `rugs_bot` profile to avoid CDP binding issues.

```python
# Profile path (from config.py)
CHROME_PROFILE_PATH = Path.home() / ".gamebot" / "chrome_profiles" / "rugs_bot"

# Launch Chrome with CDP enabled
chrome_args = [
    f"--user-data-dir={CHROME_PROFILE_PATH}",
    "--remote-debugging-port=9222",
    "--no-first-run",
]
```

### 2. BrowserBridge Singleton

Thread-safe singleton pattern for global access:

```python
# src/browser/bridge.py

_bridge_instance: BrowserBridge | None = None
_bridge_lock = threading.Lock()

def get_browser_bridge() -> BrowserBridge:
    """Get or create the singleton browser bridge instance (thread-safe)"""
    global _bridge_instance
    if _bridge_instance is None:
        with _bridge_lock:
            if _bridge_instance is None:
                _bridge_instance = BrowserBridge()
    return _bridge_instance
```

### 3. Async/Sync Bridge Pattern

Flask is synchronous, but Playwright is async. Bridge using action queue:

```python
class BrowserBridge:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._action_queue: asyncio.Queue = None
        self._running = False
        self._loop_ready = threading.Event()

    def start_async_loop(self):
        """Start background async loop for browser operations"""
        self._running = True
        self._loop_ready.clear()
        self._thread = threading.Thread(
            target=self._run_async_loop,
            daemon=True,
            name="BrowserBridge-AsyncLoop"
        )
        self._thread.start()

        # Wait for loop to be ready
        if not self._loop_ready.wait(timeout=5.0):
            logger.error("Async loop failed to start")
            self._running = False

    def _run_async_loop(self):
        """Background thread running async event loop"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._action_queue = asyncio.Queue()

        # Signal ready
        self._loop_ready.set()

        self._loop.run_until_complete(self._process_actions())

    def _queue_action(self, action: dict):
        """Queue action for async loop (thread-safe)"""
        if not self._running or not self._loop:
            return
        asyncio.run_coroutine_threadsafe(
            self._action_queue.put(action),
            self._loop
        )
```

### 4. Multi-Strategy Button Selectors

Robust button finding with fallback strategies:

```python
class SelectorStrategy:
    """Priority order: CSS → Exact Text → Starts-with → Contains → Class"""

    # CSS selectors for rugs.fun UI
    BUTTON_CSS_SELECTORS = {
        "BUY": [
            'div[class*="_buttonSection_"]:nth-child(1)',
            'button[class*="buy" i]',
            '[data-action="buy"]',
        ],
        "SELL": [
            'div[class*="_buttonSection_"]:nth-child(2)',
            'button[class*="sell" i]',
        ],
        "SIDEBET": [
            ".bet-button",
            'button[class*="side" i]',
        ],
        "X": [  # Clear button
            'button[class*="_clearButton_"]',
            '[class*="_inputActions_"] button',
        ],
    }

    # Text patterns for dynamic button text
    BUTTON_TEXT_PATTERNS = {
        "BUY": ["BUY", "Buy", "buy"],
        "SELL": ["SELL", "Sell", "sell"],
        "SIDEBET": ["SIDEBET", "SIDE", "Side", "sidebet"],
        "X": ["×", "✕", "X", "x"],  # Clear button variants
    }
```

### 5. CDP WebSocket Interception

Capture WebSocket frames via CDP Network domain:

```python
# src/sources/cdp_websocket_interceptor.py

class CDPWebSocketInterceptor:
    async def connect(self, cdp_session) -> bool:
        """Connect to CDP session and start interception"""
        self._session = cdp_session

        # Enable Network domain
        await self._session.send("Network.enable")

        # Register handlers
        self._session.on("Network.webSocketCreated", self._on_ws_created)
        self._session.on("Network.webSocketFrameReceived", self._on_ws_frame)

        return True

    def _on_ws_frame(self, params):
        """Handle incoming WebSocket frame"""
        payload = params.get("response", {}).get("payloadData", "")

        # Parse Socket.IO frame
        if payload.startswith("42"):  # Socket.IO message
            json_str = payload[2:]  # Strip "42" prefix
            event_data = json.loads(json_str)
            event_name = event_data[0]
            event_payload = event_data[1] if len(event_data) > 1 else {}

            # Emit to callback
            if self.on_event:
                self.on_event({
                    "event": event_name,
                    "data": event_payload,
                    "source": "cdp"
                })
```

### 6. Force Socket.IO Reconnection

Pre-existing WebSockets can't be intercepted. Force reconnection after CDP setup:

```python
async def _force_socketio_reconnect(self):
    """Force Socket.IO to reconnect for CDP capture"""
    reconnect_js = """
    () => {
        // Search for Socket.IO instance
        let socket = window.socketService || window.socket;

        if (!socket) {
            for (const key of Object.keys(window)) {
                const obj = window[key];
                if (obj && typeof obj.disconnect === 'function'
                    && typeof obj.connect === 'function') {
                    socket = obj;
                    break;
                }
            }
        }

        if (socket) {
            socket.disconnect();
            setTimeout(() => socket.connect(), 500);
            return { reconnected: true };
        }
        return { reconnected: false };
    }
    """
    await self.cdp_manager.page.evaluate(reconnect_js)
```

## Integration Points

### With EventBus

```python
# In BrowserBridge._start_cdp_interception()
def on_cdp_event(event):
    # Publish to EventBus for all subscribers
    self._event_bus.publish(Events.WS_RAW_EVENT, event)

    # Also catalog for RAG
    self._rag_ingester.catalog(event)

self._cdp_interceptor.on_event = on_cdp_event
```

### With Flask (BrowserService)

```python
# src/recording_ui/services/browser_service.py

class BrowserService:
    """Flask-compatible wrapper for BrowserBridge"""

    def _get_bridge(self):
        """Lazy-load with double-checked locking"""
        if self._bridge is None:
            with self._bridge_lock:
                if self._bridge is None:
                    from browser.bridge import BrowserBridge
                    self._bridge = BrowserBridge()
        return self._bridge

    def connect(self) -> dict:
        """Connect to browser (sync API for Flask)"""
        bridge = self._get_bridge()
        bridge.connect()
        time.sleep(0.5)  # Wait for connection
        return {"connected": bridge.is_connected()}

    def click_buy(self) -> dict:
        """Execute BUY (sync API)"""
        bridge = self._get_bridge()
        bridge.on_buy_clicked()
        return {"success": True}
```

## Configuration

### Environment Variables

```bash
CDP_PORT=9222                    # Chrome DevTools port
CHROME_PROFILE=rugs_bot          # Profile directory name
CHROME_PROFILE_PATH=~/.gamebot/chrome_profiles/rugs_bot
```

### Timeouts

```python
# In BrowserBridge
CLICK_TIMEOUT = 10.0             # Button click timeout
ACTION_TIMEOUT = 10.0            # General action timeout
WALLET_DETECTION_TIMEOUT = 60.0  # Wallet detection timeout
CONNECT_TIMEOUT = 60.0           # Full connection timeout
MAX_RETRIES = 3                  # Click retry attempts
RETRY_BASE_DELAY = 0.5           # Exponential backoff base
```

## Gotchas

1. **Profile Path**: Default Chrome profile (`~/.config/google-chrome/`) has CDP binding issues. Always use `rugs_bot` profile.

2. **Async Loop Ready**: Must wait for `_loop_ready.wait()` before queuing actions, otherwise race condition.

3. **Button Text Mismatch**: Button text is dynamic (e.g., "BUY+0.030 SOL"). Use `starts-with` matching, not exact match.

4. **X vs X2**: Single-char patterns like "X" can match "X2". CSS selectors take priority to prevent this.

5. **Visibility Check**: Standard visibility checks fail for `position: fixed` elements. Custom JS visibility detection required.

6. **Socket.IO Prefix**: WebSocket frames have "42" prefix for Socket.IO messages. Strip before JSON parsing.

7. **Event Bus ID**: Keep reference to event_bus, not just its id(), for proper subscription tracking.
