"""
Foundation Python Client - Async WebSocket client for Foundation Service.

Python equivalent of FoundationWSClient (JS). Provides:
- Async WebSocket connection with exponential backoff reconnection
- Event subscription/unsubscription with wildcard support
- Event buffering for late subscribers
- Latency metrics tracking
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClientMetrics:
    """Connection and performance metrics for FoundationClient."""

    connected: bool = False
    message_count: int = 0
    last_message_time: int | None = None
    connection_attempts: int = 0
    last_connected_time: int | None = None
    average_latency: float = 0.0

    def to_dict(self) -> dict:
        """Serialize metrics to dict."""
        return {
            "connected": self.connected,
            "message_count": self.message_count,
            "last_message_time": self.last_message_time,
            "connection_attempts": self.connection_attempts,
            "last_connected_time": self.last_connected_time,
            "average_latency": self.average_latency,
        }


class FoundationClient:
    """
    Async WebSocket client for Foundation Service.

    Mirrors the FoundationWSClient (JS) API for consistency.

    Usage:
        client = FoundationClient()
        client.on('game.tick', lambda e: print(e))
        await client.connect()
    """

    def __init__(
        self,
        url: str = "ws://localhost:9000/feed",
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
        reconnect_multiplier: float = 1.5,
        max_buffer_size: int = 10,
    ):
        """
        Initialize Foundation client.

        Args:
            url: WebSocket URL for Foundation Service
            reconnect_delay: Initial reconnect delay in seconds
            max_reconnect_delay: Maximum reconnect delay in seconds
            reconnect_multiplier: Backoff multiplier for reconnection
            max_buffer_size: Maximum events to buffer per event type
        """
        self.url = url
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.reconnect_multiplier = reconnect_multiplier
        self.max_buffer_size = max_buffer_size

        # Connection state
        self._ws = None
        self._is_connected = False
        self._intentional_close = False
        self._current_reconnect_delay = reconnect_delay

        # Event listeners: event_type -> set of callbacks
        self._listeners: dict[str, set[Callable]] = {}

        # Recent event buffer: event_type -> list of events
        self._recent_events: dict[str, list[dict]] = {}

        # Metrics
        self._metrics = ClientMetrics()
        self._latencies: list[float] = []

    def is_connected(self) -> bool:
        """Check if client is currently connected."""
        return self._is_connected

    def get_metrics(self) -> ClientMetrics:
        """
        Get current connection metrics.

        Returns:
            ClientMetrics with current stats
        """
        # Update average latency
        if self._latencies:
            self._metrics.average_latency = sum(self._latencies) / len(self._latencies)
        return self._metrics

    def on(self, event_type: str, callback: Callable[[dict], None]) -> Callable[[], None]:
        """
        Register an event listener.

        Args:
            event_type: Event type to listen for (e.g., 'game.tick', '*' for all)
            callback: Function to call when event is received

        Returns:
            Unsubscribe function
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = set()

        self._listeners[event_type].add(callback)

        # Return unsubscribe function
        def unsubscribe():
            if event_type in self._listeners:
                self._listeners[event_type].discard(callback)

        return unsubscribe

    def _emit(self, event_type: str, data: dict) -> None:
        """
        Emit event to all registered listeners.

        Args:
            event_type: The event type
            data: Event data to emit
        """
        # Emit to specific type listeners
        if event_type in self._listeners:
            for callback in list(self._listeners[event_type]):
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in listener for {event_type}: {e}")

        # Emit to wildcard listeners
        if "*" in self._listeners:
            for callback in list(self._listeners["*"]):
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in wildcard listener: {e}")

    def _handle_message(self, message: dict) -> None:
        """
        Handle incoming message from Foundation Service.

        Args:
            message: Parsed JSON message
        """
        event_type = message.get("type", "unknown")
        ts = message.get("ts")

        # Update metrics
        self._metrics.message_count += 1
        self._metrics.last_message_time = int(time.time() * 1000)

        # Calculate latency
        if ts:
            latency = self._metrics.last_message_time - ts
            self._latencies.append(latency)
            if len(self._latencies) > 100:
                self._latencies.pop(0)
            self._metrics.average_latency = sum(self._latencies) / len(self._latencies)

        # Buffer event
        if event_type not in self._recent_events:
            self._recent_events[event_type] = []
        buffer = self._recent_events[event_type]
        buffer.append(message)
        if len(buffer) > self.max_buffer_size:
            buffer.pop(0)

        # Emit to listeners
        self._emit(event_type, message)

    def get_recent_events(self, event_type: str) -> list[dict]:
        """
        Get recent events of a specific type.

        Useful for late subscribers to catch up.

        Args:
            event_type: Event type to get

        Returns:
            List of recent events (up to max_buffer_size)
        """
        return self._recent_events.get(event_type, [])

    def _on_connected(self) -> None:
        """Handle successful connection."""
        self._is_connected = True
        self._current_reconnect_delay = self.reconnect_delay
        self._metrics.connected = True
        self._metrics.last_connected_time = int(time.time() * 1000)

        logger.info("[Foundation] Connected")
        self._emit("connection", {"connected": True})

    def _on_disconnected(self, code: int = 1000, reason: str = "") -> None:
        """Handle disconnection."""
        self._is_connected = False
        self._metrics.connected = False

        logger.info(f"[Foundation] Disconnected (code: {code})")
        self._emit("connection", {"connected": False, "code": code, "reason": reason})

    async def connect(self) -> None:
        """
        Connect to Foundation Service.

        Will automatically reconnect with exponential backoff if disconnected
        (unless disconnect() was called intentionally).
        """
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets package required: pip install websockets")

        self._intentional_close = False
        self._metrics.connection_attempts += 1

        logger.info(f"[Foundation] Connecting to {self.url}...")

        try:
            async with websockets.connect(self.url) as ws:
                self._ws = ws
                self._on_connected()

                try:
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            self._handle_message(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"[Foundation] Failed to parse message: {e}")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.debug(f"[Foundation] Connection error: {e}")
                finally:
                    self._on_disconnected()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[Foundation] Connect failed: {e}")
            self._on_disconnected(code=1006, reason=str(e))

            # Schedule reconnect if not intentional
            if not self._intentional_close:
                await self._schedule_reconnect()

    async def _schedule_reconnect(self) -> None:
        """Schedule reconnection with exponential backoff."""
        delay = self._current_reconnect_delay
        logger.info(f"[Foundation] Reconnecting in {delay}s...")

        await asyncio.sleep(delay)

        # Update delay for next attempt
        self._current_reconnect_delay = min(
            self._current_reconnect_delay * self.reconnect_multiplier,
            self.max_reconnect_delay,
        )

        if not self._intentional_close:
            await self.connect()

    async def disconnect(self) -> None:
        """
        Disconnect from Foundation Service.

        Prevents automatic reconnection.
        """
        self._intentional_close = True

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._is_connected = False
        self._metrics.connected = False
