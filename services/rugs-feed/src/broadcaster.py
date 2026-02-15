"""
WebSocket broadcaster for Rugs Feed Service.

Broadcasts raw Socket.IO events to downstream subscribers.
Mirror of Foundation broadcaster pattern, but without normalization.
"""

import asyncio
import json
import logging
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import CapturedEvent

logger = logging.getLogger(__name__)


@dataclass
class BroadcasterStats:
    """Statistics for the broadcaster."""

    events_broadcast: int = 0
    events_dropped: int = 0
    clients_connected: int = 0
    clients_disconnected: int = 0


class RawEventBroadcaster:
    """
    WebSocket broadcaster for raw rugs.fun events.

    Downstream services connect to receive the full event stream.
    Protocol: Unidirectional (server -> client only).
    Clients can send 'ping' for keepalive.
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize broadcaster.

        Args:
            max_queue_size: Maximum events to queue before dropping
        """
        self._clients: set[weakref.ref] = set()
        self._stats = BroadcasterStats()
        self._event_queue: asyncio.Queue | None = None
        self._is_running = False
        self._max_queue_size = max_queue_size
        self._broadcast_task: asyncio.Task | None = None

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        # Clean up dead references
        self._clients = {ref for ref in self._clients if ref() is not None}
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        """Whether the broadcaster is running."""
        return self._is_running

    def start(self) -> None:
        """Start the broadcast queue (call before event loop)."""
        self._event_queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._is_running = True
        logger.info("RawEventBroadcaster started")

    async def start_broadcast_loop(self) -> None:
        """Start the background broadcast loop."""
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    def stop(self) -> None:
        """Stop the broadcaster."""
        self._is_running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
        logger.info("RawEventBroadcaster stopped")

    async def register(self, websocket) -> None:
        """
        Register a WebSocket client.

        Args:
            websocket: FastAPI WebSocket instance
        """
        client_ref = weakref.ref(websocket)
        self._clients.add(client_ref)
        self._stats.clients_connected += 1
        logger.info(f"Client registered (total: {self.client_count})")

    async def unregister(self, websocket) -> None:
        """
        Unregister a WebSocket client.

        Args:
            websocket: FastAPI WebSocket instance
        """
        # Find and remove the reference
        to_remove = None
        for ref in self._clients:
            if ref() is websocket:
                to_remove = ref
                break
        if to_remove:
            self._clients.discard(to_remove)
        self._stats.clients_disconnected += 1
        logger.info(f"Client unregistered (total: {self.client_count})")

    def broadcast(self, event: "CapturedEvent") -> None:
        """
        Queue an event for broadcasting.

        Thread-safe: Can be called from any context.

        Args:
            event: CapturedEvent to broadcast
        """
        if self._event_queue is None:
            logger.warning("Broadcast called before start()")
            return

        try:
            # Convert to JSON-serializable dict
            event_dict = {
                "type": "raw_event",
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "game_id": event.game_id,
            }
            self._event_queue.put_nowait(event_dict)
        except asyncio.QueueFull:
            self._stats.events_dropped += 1
            logger.warning("Event queue full, dropping event")

    async def _broadcast_loop(self) -> None:
        """Process queued events and broadcast to clients."""
        logger.info("Broadcast loop started")
        while self._is_running:
            try:
                # Wait for event with timeout
                event_dict = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._send_to_all(event_dict)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    async def _send_to_all(self, event_dict: dict) -> None:
        """Send event to all connected clients."""
        if not self._clients:
            return

        message = json.dumps(event_dict)

        # Get live websockets
        live_clients = []
        dead_refs = []

        for ref in self._clients:
            ws = ref()
            if ws is not None:
                live_clients.append(ws)
            else:
                dead_refs.append(ref)

        # Clean up dead refs
        for ref in dead_refs:
            self._clients.discard(ref)

        # Broadcast to all live clients
        if live_clients:
            await asyncio.gather(
                *[self._safe_send(ws, message) for ws in live_clients],
                return_exceptions=True,
            )
            self._stats.events_broadcast += 1

    async def _safe_send(self, websocket, message: str) -> None:
        """Safely send message to websocket, handling errors."""
        try:
            await websocket.send_text(message)
        except Exception:
            pass  # Client disconnected, will be cleaned up

    def get_stats(self) -> dict:
        """Get broadcaster statistics."""
        return {
            "client_count": self.client_count,
            "is_running": self.is_running,
            "events_broadcast": self._stats.events_broadcast,
            "events_dropped": self._stats.events_dropped,
            "clients_connected": self._stats.clients_connected,
            "clients_disconnected": self._stats.clients_disconnected,
            "queue_size": self._event_queue.qsize() if self._event_queue else 0,
        }


# Global broadcaster instance
_broadcaster: RawEventBroadcaster | None = None


def get_broadcaster() -> RawEventBroadcaster:
    """Get the global broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = RawEventBroadcaster()
    return _broadcaster
