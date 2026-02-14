# src/foundation/broadcaster.py
"""WebSocket broadcaster for Foundation Service."""

import asyncio
import json
import logging
import weakref
from dataclasses import dataclass

from foundation.normalizer import NormalizedEvent

logger = logging.getLogger(__name__)


@dataclass
class BroadcasterStats:
    """Statistics for the broadcaster."""

    events_broadcast: int = 0
    events_dropped: int = 0
    clients_connected: int = 0
    clients_disconnected: int = 0


class WebSocketBroadcaster:
    """
    WebSocket server that broadcasts normalized events to all connected clients.

    Protocol: Unidirectional (server -> client only).
    Clients can send 'ping' for keepalive, nothing else.
    """

    def __init__(self, host: str = "localhost", port: int = 9000):
        self.host = host
        self.port = port
        self._clients: set[weakref.ref] = set()
        self._server = None
        self._is_running = False
        self._stats = BroadcasterStats()
        self._event_queue: asyncio.Queue = None

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

    async def start(self) -> None:
        """Start the WebSocket server."""
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets package required: pip install websockets")

        self._event_queue = asyncio.Queue()
        self._is_running = True

        logger.info(f"Starting WebSocket broadcaster on ws://{self.host}:{self.port}/feed")

        async with websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        ) as server:
            self._server = server

            # Run broadcast loop
            try:
                await self._broadcast_loop()
            except asyncio.CancelledError:
                pass

        self._is_running = False
        logger.info("WebSocket broadcaster stopped")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._is_running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(self, websocket) -> None:
        """Handle a connected client."""
        client_ref = weakref.ref(websocket)
        self._clients.add(client_ref)
        self._stats.clients_connected += 1

        client_id = id(websocket)
        remote = getattr(websocket, "remote_address", "unknown")
        logger.info(f"Client {client_id} connected from {remote}")

        try:
            async for message in websocket:
                # Only handle ping messages
                try:
                    data = json.loads(message)
                    if data.get("action") == "ping":
                        await websocket.send(json.dumps({"type": "pong", "ts": data.get("ts")}))
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug(f"Client {client_id} error: {e}")
        finally:
            self._clients.discard(client_ref)
            self._stats.clients_disconnected += 1
            logger.info(f"Client {client_id} disconnected")

    async def _broadcast_loop(self) -> None:
        """Process queued events and broadcast to clients."""
        while self._is_running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._send_to_all(event)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    async def _send_to_all(self, event: NormalizedEvent) -> None:
        """Send event to all connected clients."""
        if not self._clients:
            return

        message = json.dumps(event.to_dict())

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
                *[self._safe_send(ws, message) for ws in live_clients], return_exceptions=True
            )
            self._stats.events_broadcast += 1

    async def _safe_send(self, websocket, message: str) -> None:
        """Safely send message to websocket, handling errors."""
        try:
            await websocket.send(message)
        except Exception:
            pass  # Client disconnected, will be cleaned up

    def broadcast(self, event: NormalizedEvent) -> None:
        """
        Queue an event for broadcasting.

        Thread-safe: Can be called from any thread.
        """
        if self._event_queue is not None:
            try:
                self._event_queue.put_nowait(event)
            except asyncio.QueueFull:
                self._stats.events_dropped += 1
                logger.warning("Event queue full, dropping event")

    def get_stats(self) -> dict:
        """Get broadcaster statistics."""
        return {
            "client_count": self.client_count,
            "is_running": self.is_running,
            "events_broadcast": self._stats.events_broadcast,
            "events_dropped": self._stats.events_dropped,
            "clients_connected": self._stats.clients_connected,
            "clients_disconnected": self._stats.clients_disconnected,
        }
