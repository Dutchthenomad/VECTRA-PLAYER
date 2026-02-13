"""
Event Bus Implementation

Pub/sub messaging pattern for decoupling producers and consumers
of game events throughout VECTRA-PLAYER.

Usage:
    from event_bus import EventBus, Events

    bus = EventBus()

    @bus.subscribe(Events.GAME_TICK)
    def on_tick(event):
        print(f"Tick {event['tick']} at price {event['price']}")

    bus.publish(Events.GAME_TICK, {"tick": 100, "price": 2.5})
"""

import logging
import queue
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Events(Enum):
    """Event type enumeration."""

    # Connection events
    WS_CONNECTED = "ws.connected"
    WS_DISCONNECTED = "ws.disconnected"
    WS_RAW_EVENT = "ws.raw_event"

    # Game events
    GAME_STARTED = "game.started"
    GAME_TICK = "game.tick"
    GAME_ENDED = "game.ended"

    # Player events
    PLAYER_UPDATE = "player.update"
    PLAYER_TRADE = "player.trade"

    # Sidebet events
    SIDEBET_PLACED = "sidebet.placed"
    SIDEBET_RESULT = "sidebet.result"

    # System events
    RECORDING_STARTED = "recording.started"
    RECORDING_STOPPED = "recording.stopped"
    ERROR = "error"


@dataclass
class EventEnvelope:
    """Wraps event data with metadata."""

    event_type: Events
    data: dict
    timestamp: float
    source: str = "unknown"


class EventBus:
    """
    Simple pub/sub event bus.

    Features:
    - Synchronous event dispatch
    - Multiple subscribers per event
    - Wildcard subscription (all events)
    - Thread-safe

    Example:
        bus = EventBus()

        # Subscribe with decorator
        @bus.subscribe(Events.GAME_TICK)
        def handle_tick(event):
            print(event)

        # Subscribe inline
        bus.subscribe(Events.PLAYER_UPDATE)(lambda e: print(e))

        # Publish
        bus.publish(Events.GAME_TICK, {"tick": 1, "price": 1.5})
    """

    def __init__(self):
        self._subscribers: dict[Events, list[Callable]] = defaultdict(list)
        self._wildcard_subscribers: list[Callable] = []
        self._lock = threading.RLock()

    def subscribe(self, event_type: Events | None = None):
        """
        Subscribe to an event type.

        Args:
            event_type: Event to subscribe to, or None for all events

        Returns:
            Decorator function

        Usage:
            @bus.subscribe(Events.GAME_TICK)
            def handler(event):
                pass
        """

        def decorator(func: Callable):
            with self._lock:
                if event_type is None:
                    self._wildcard_subscribers.append(func)
                else:
                    self._subscribers[event_type].append(func)
            return func

        return decorator

    def unsubscribe(self, event_type: Events | None, func: Callable):
        """Remove a subscriber."""
        with self._lock:
            if event_type is None:
                if func in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(func)
            else:
                if func in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(func)

    def publish(self, event_type: Events, data: dict, source: str = "unknown"):
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event payload
            source: Event source identifier
        """
        import time

        envelope = EventEnvelope(
            event_type=event_type, data=data, timestamp=time.time(), source=source
        )

        with self._lock:
            # Notify specific subscribers
            for handler in self._subscribers[event_type]:
                try:
                    handler(envelope)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")

            # Notify wildcard subscribers
            for handler in self._wildcard_subscribers:
                try:
                    handler(envelope)
                except Exception as e:
                    logger.error(f"Wildcard handler error: {e}")

    def clear(self):
        """Remove all subscribers."""
        with self._lock:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()


class AsyncEventBus(EventBus):
    """
    Async event bus with queue-based dispatch.

    Events are queued and processed in a separate thread.
    """

    def __init__(self, max_queue_size: int = 1000):
        super().__init__()
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the event dispatch thread."""
        self._running = True
        self._thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the event dispatch thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _dispatch_loop(self):
        """Background thread that dispatches queued events."""
        while self._running:
            try:
                envelope = self._queue.get(timeout=0.1)
                self._dispatch(envelope)
            except queue.Empty:
                continue

    def _dispatch(self, envelope: EventEnvelope):
        """Dispatch a single event."""
        with self._lock:
            for handler in self._subscribers[envelope.event_type]:
                try:
                    handler(envelope)
                except Exception as e:
                    logger.error(f"Async handler error: {e}")

            for handler in self._wildcard_subscribers:
                try:
                    handler(envelope)
                except Exception as e:
                    logger.error(f"Async wildcard handler error: {e}")

    def publish(self, event_type: Events, data: dict, source: str = "unknown"):
        """Queue an event for async dispatch."""
        import time

        envelope = EventEnvelope(
            event_type=event_type, data=data, timestamp=time.time(), source=source
        )

        try:
            self._queue.put_nowait(envelope)
        except queue.Full:
            logger.warning("Event queue full, dropping event")


# Singleton instance
_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance


# Example usage
if __name__ == "__main__":
    bus = EventBus()

    # Subscribe to game ticks
    @bus.subscribe(Events.GAME_TICK)
    def on_tick(event: EventEnvelope):
        print(f"Tick: {event.data['tick']} Price: {event.data['price']}")

    # Subscribe to all events (wildcard)
    @bus.subscribe(None)
    def log_all(event: EventEnvelope):
        print(f"[LOG] {event.event_type.value}: {event.data}")

    # Publish events
    bus.publish(Events.GAME_STARTED, {"game_id": "abc123"})
    bus.publish(Events.GAME_TICK, {"tick": 1, "price": 1.0})
    bus.publish(Events.GAME_TICK, {"tick": 2, "price": 1.2})
    bus.publish(Events.GAME_ENDED, {"game_id": "abc123", "peak": 5.5})
