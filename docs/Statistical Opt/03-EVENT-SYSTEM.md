# 03 - Event System

## Purpose

The EventBus provides decoupled pub/sub messaging between system components:
1. WebSocket interceptor publishes game events
2. EventStore subscribes for persistence
3. BrowserService subscribes for UI updates
4. LiveBacktestService subscribes for paper trading

## Dependencies

```python
# Core module
from services.event_bus import EventBus, Events, event_bus
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           EventBus                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Publishers                    Events                 Subscribers   │
│  ──────────                    ──────                 ───────────   │
│                                                                     │
│  CDPInterceptor ──────────▶ WS_RAW_EVENT ──────────▶ EventStore    │
│                                    │                                │
│                                    ├──────────▶ BrowserService      │
│                                    │                                │
│                                    └──────────▶ RAGIngester         │
│                                                                     │
│  LiveBacktest ────────────▶ GAME_TICK ─────────────▶ EventStore    │
│                                                                     │
│  Dashboard ───────────────▶ TRADE_BUY ─────────────▶ EventStore    │
│                           ▶ TRADE_SELL                              │
│                           ▶ TRADE_SIDEBET                           │
│                                                                     │
│  BrowserBridge ───────────▶ BUTTON_PRESS ──────────▶ EventStore    │
│                                                     (RL Training)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Event Types Enum

```python
# src/services/event_bus.py

from enum import Enum

class Events(Enum):
    """All event types in the system"""

    # WebSocket events
    WS_RAW_EVENT = "ws_raw_event"
    WS_CONNECTED = "ws_connected"
    WS_DISCONNECTED = "ws_disconnected"

    # Game events
    GAME_TICK = "game_tick"
    GAME_START = "game_start"
    GAME_END = "game_end"

    # Player events
    PLAYER_UPDATE = "player_update"

    # Trade events
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    TRADE_SIDEBET = "trade_sidebet"
    TRADE_CONFIRMED = "trade_confirmed"

    # UI events
    BUTTON_PRESS = "button_press"
```

### 2. EventBus Implementation

```python
class EventBus:
    """Thread-safe publish/subscribe event bus"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = threading.RLock()
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def subscribe(self, event: Events, callback: Callable, weak: bool = True):
        """
        Subscribe to an event type.

        Args:
            event: Event type to subscribe to
            callback: Function to call when event fires
            weak: If True, use weak reference (allows garbage collection)
        """
        with self._lock:
            event_name = event.value
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []

            if weak:
                self._subscribers[event_name].append(weakref.ref(callback))
            else:
                self._subscribers[event_name].append(callback)

    def unsubscribe(self, event: Events, callback: Callable):
        """Remove a subscription"""
        with self._lock:
            event_name = event.value
            if event_name in self._subscribers:
                self._subscribers[event_name] = [
                    c for c in self._subscribers[event_name]
                    if (callable(c) and c != callback) or
                       (hasattr(c, '__call__') and c() != callback)
                ]

    def publish(self, event: Events, data: Any = None):
        """
        Publish an event to all subscribers.

        Args:
            event: Event type
            data: Event payload (any serializable data)
        """
        wrapped = {
            "name": event.value,
            "data": data,
            "timestamp": time.time()
        }
        self._queue.put((event.value, wrapped))

    def has_subscribers(self, event: Events) -> bool:
        """Check if event has any subscribers"""
        with self._lock:
            return len(self._subscribers.get(event.value, [])) > 0
```

### 3. Background Processing Thread

```python
def start(self):
    """Start the event processing thread"""
    if self._running:
        return

    self._running = True
    self._thread = threading.Thread(
        target=self._process_events,
        daemon=True,
        name="EventBus-Processor"
    )
    self._thread.start()

def _process_events(self):
    """Process events from queue in background thread"""
    while self._running:
        try:
            event_name, wrapped = self._queue.get(timeout=0.1)
            self._dispatch(event_name, wrapped)
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Event processing error: {e}")

def _dispatch(self, event_name: str, wrapped: dict):
    """Dispatch event to all subscribers"""
    with self._lock:
        subscribers = self._subscribers.get(event_name, []).copy()

    for callback in subscribers:
        try:
            # Handle weak references
            if hasattr(callback, '__call__') and not callable(callback):
                callback = callback()
                if callback is None:
                    continue

            callback(wrapped)
        except Exception as e:
            logger.error(f"Subscriber error for {event_name}: {e}")
```

### 4. Global Singleton

```python
# Global event bus instance
event_bus = EventBus()

# Usage
from services.event_bus import event_bus, Events

# Publisher
event_bus.publish(Events.GAME_TICK, {"tick": 100, "price": 2.5})

# Subscriber
def on_game_tick(wrapped):
    data = wrapped.get("data", {})
    print(f"Tick: {data['tick']}, Price: {data['price']}")

event_bus.subscribe(Events.GAME_TICK, on_game_tick, weak=False)
```

### 5. Event Unwrapping Pattern

Events are wrapped with metadata. Subscribers must unwrap:

```python
def _on_ws_raw_event(self, wrapped: dict):
    """Handle wrapped event from EventBus"""

    # EventBus wraps: {"name": event.value, "data": actual_data}
    data = wrapped.get("data", wrapped)

    # For double-wrapped events (EventBus + BrowserBridge)
    if "data" in data and "event" not in data:
        data = data.get("data", {})

    # Now data has the actual event
    event_name = data.get("event")
    event_data = data.get("data", {})
```

## Integration Points

### EventStore Subscription

```python
# src/services/event_store/service.py

class EventStoreService:
    def start(self):
        """Subscribe to all relevant events"""
        self._event_bus.subscribe(
            Events.WS_RAW_EVENT,
            self._on_ws_raw_event,
            weak=False  # Prevent garbage collection
        )
        self._event_bus.subscribe(Events.GAME_TICK, self._on_game_tick, weak=False)
        self._event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update, weak=False)
        self._event_bus.subscribe(Events.TRADE_BUY, self._on_trade_buy, weak=False)
        self._event_bus.subscribe(Events.TRADE_SELL, self._on_trade_sell, weak=False)
        self._event_bus.subscribe(Events.TRADE_SIDEBET, self._on_trade_sidebet, weak=False)
        self._event_bus.subscribe(Events.BUTTON_PRESS, self._on_button_press, weak=False)
```

### BrowserBridge Publication

```python
# src/browser/bridge.py

def on_cdp_event(event):
    # Check for subscribers before publishing
    has_subs = self._event_bus.has_subscribers(Events.WS_RAW_EVENT)
    if has_subs:
        self._event_bus.publish(Events.WS_RAW_EVENT, event)
    else:
        logger.warning("No EventBus subscribers - event dropped")

self._cdp_interceptor.on_event = on_cdp_event
```

### Flask App Startup

```python
# src/recording_ui/app.py

def _start_background_services():
    """Start EventBus in correct process"""
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        event_bus.start()
        logger.info("EventBus processing thread started")

_start_background_services()
```

## Configuration

### Thread Safety Settings

```python
# EventBus uses RLock for reentrant locking
self._lock = threading.RLock()

# Queue timeout prevents blocking forever
event_name, wrapped = self._queue.get(timeout=0.1)
```

### Weak References

```python
# Default: weak=True (allows garbage collection)
event_bus.subscribe(Events.GAME_TICK, callback)

# For services that must persist: weak=False
event_bus.subscribe(Events.GAME_TICK, callback, weak=False)
```

## Event Flow Examples

### 1. Game Tick Flow

```
gameStateUpdate → CDPInterceptor → EventBus.publish(WS_RAW_EVENT)
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              EventStore         BrowserService      LiveBacktest
              (persist)          (UI update)         (paper trade)
```

### 2. Trade Action Flow

```
Dashboard BUY button → BrowserService.click_buy()
                            │
                            ▼
                      BrowserBridge.on_buy_clicked()
                            │
                            ├── Queue CDP click action
                            │
                            └── EventBus.publish(TRADE_BUY)
                                        │
                                        ▼
                                  EventStore
                                  (persist action)
```

### 3. Button Press (RL Training)

```
UI button click → BrowserBridge.on_increment_clicked("+0.01")
                        │
                        ├── Queue CDP click
                        │
                        └── Create ButtonEvent with context
                                    │
                                    ▼
                            EventBus.publish(BUTTON_PRESS)
                                    │
                                    ▼
                            EventStore._on_button_press()
                            (persist for RL training)
```

## Gotchas

1. **Weak References**: Use `weak=False` for service subscriptions. Weak references get garbage collected.

2. **Event Wrapping**: EventBus wraps data. Always unwrap: `data = wrapped.get("data", wrapped)`

3. **Double Wrapping**: BrowserBridge may wrap, then EventBus wraps again. Handle nested unwrapping.

4. **Reloader Duplicate**: Flask debug reloader starts services twice. Guard with `WERKZEUG_RUN_MAIN`.

5. **Subscriber Errors**: Subscriber exceptions don't stop other subscribers. Errors are logged and swallowed.

6. **Thread Safety**: Publishing is thread-safe. Queue handles synchronization.

7. **No Subscribers Warning**: Check `has_subscribers()` to detect misconfigured pipelines.
