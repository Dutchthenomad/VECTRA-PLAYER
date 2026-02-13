"""
Multi-channel WebSocket broadcaster.

Reuses the RawEventBroadcaster pattern from rugs-feed but with
channel-based routing. Each channel maintains independent client sets.
"""

from __future__ import annotations

import asyncio
import logging
import weakref
from dataclasses import dataclass

from .models import Channel, SanitizedEvent

logger = logging.getLogger(__name__)


@dataclass
class ChannelStats:
    """Per-channel statistics."""

    events_sent: int = 0
    events_dropped: int = 0


@dataclass
class BroadcasterStats:
    """Global broadcaster statistics."""

    total_events: int = 0
    total_dropped: int = 0
    clients_connected: int = 0
    clients_disconnected: int = 0


class ChannelBroadcaster:
    """Multi-channel WebSocket broadcaster.

    Channels:
    - /feed/game:    GameTick events
    - /feed/stats:   SessionStats events
    - /feed/trades:  Annotated Trade events
    - /feed/history: GameHistoryRecord events
    - /feed/all:     All of the above
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._channels: dict[Channel, set[weakref.ref]] = {ch: set() for ch in Channel}
        self._channel_stats: dict[Channel, ChannelStats] = {ch: ChannelStats() for ch in Channel}
        self._global_stats = BroadcasterStats()
        self._queue: asyncio.Queue | None = None
        self._max_queue_size = max_queue_size
        self._is_running = False
        self._broadcast_task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Initialize the broadcast queue."""
        self._queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._is_running = True
        logger.info("ChannelBroadcaster started")

    def stop(self) -> None:
        """Stop the broadcaster."""
        self._is_running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
        logger.info("ChannelBroadcaster stopped")

    async def start_broadcast_loop(self) -> None:
        """Start the background broadcast loop."""
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    def client_count(self, channel: Channel | None = None) -> int:
        """Number of connected clients, optionally filtered by channel."""
        if channel is not None:
            self._cleanup_channel(channel)
            return len(self._channels[channel])
        # Total unique clients across all channels
        all_clients: set[int] = set()
        for ch in Channel:
            self._cleanup_channel(ch)
            for ref in self._channels[ch]:
                ws = ref()
                if ws is not None:
                    all_clients.add(id(ws))
        return len(all_clients)

    async def subscribe(self, websocket, channel: Channel) -> None:
        """Subscribe a WebSocket client to a channel."""
        ref = weakref.ref(websocket)
        self._channels[channel].add(ref)
        self._global_stats.clients_connected += 1
        logger.info(
            f"Client subscribed to {channel.value} (total on channel: {self.client_count(channel)})"
        )

    async def unsubscribe(self, websocket, channel: Channel) -> None:
        """Unsubscribe a WebSocket client from a channel."""
        to_remove = None
        for ref in self._channels[channel]:
            if ref() is websocket:
                to_remove = ref
                break
        if to_remove:
            self._channels[channel].discard(to_remove)
        self._global_stats.clients_disconnected += 1
        logger.info(f"Client unsubscribed from {channel.value}")

    def broadcast(self, event: SanitizedEvent) -> None:
        """Queue an event for broadcast to the appropriate channel.

        Thread-safe. Events are sent to the specific channel AND /feed/all.
        """
        if self._queue is None:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._global_stats.total_dropped += 1
            logger.warning("Broadcast queue full, dropping event")

    async def _broadcast_loop(self) -> None:
        """Process queued events and send to subscribed clients."""
        logger.info("Broadcast loop started")
        while self._is_running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._send_to_channel(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")

    async def _send_to_channel(self, event: SanitizedEvent) -> None:
        """Send event to all clients subscribed to its channel."""
        message = event.model_dump_json()

        # Send to the specific channel
        channel = event.channel
        if channel != Channel.ALL:
            await self._send_to_clients(channel, message)
            self._channel_stats[channel].events_sent += 1

        # Always send to ALL channel
        await self._send_to_clients(Channel.ALL, message)
        self._channel_stats[Channel.ALL].events_sent += 1
        self._global_stats.total_events += 1

    async def _send_to_clients(self, channel: Channel, message: str) -> None:
        """Send message to all live clients on a channel."""
        clients = self._channels[channel]
        if not clients:
            return

        live = []
        dead = []
        for ref in clients:
            ws = ref()
            if ws is not None:
                live.append(ws)
            else:
                dead.append(ref)

        for ref in dead:
            clients.discard(ref)

        if live:
            await asyncio.gather(
                *[self._safe_send(ws, message) for ws in live],
                return_exceptions=True,
            )

    async def _safe_send(self, websocket, message: str) -> None:
        """Safely send a message, handling disconnected clients."""
        try:
            await websocket.send_text(message)
        except Exception:
            pass

    def _cleanup_channel(self, channel: Channel) -> None:
        """Remove dead references from a channel."""
        self._channels[channel] = {ref for ref in self._channels[channel] if ref() is not None}

    def get_stats(self) -> dict:
        """Return broadcaster statistics."""
        channel_info = {}
        for ch in Channel:
            self._cleanup_channel(ch)
            channel_info[ch.value] = {
                "clients": len(self._channels[ch]),
                "events_sent": self._channel_stats[ch].events_sent,
            }
        return {
            "is_running": self._is_running,
            "total_events": self._global_stats.total_events,
            "total_dropped": self._global_stats.total_dropped,
            "total_clients_connected": self._global_stats.clients_connected,
            "total_clients_disconnected": self._global_stats.clients_disconnected,
            "queue_size": self._queue.qsize() if self._queue else 0,
            "channels": channel_info,
        }
