"""
WebSocket client connecting to rugs-feed upstream service.

Connects to ws://rugs-feed:9016/feed (Docker) or ws://localhost:9016/feed (local).
Handles auto-reconnection with exponential backoff and ping/pong keepalive.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from enum import Enum

import websockets
import websockets.exceptions

logger = logging.getLogger(__name__)

DEFAULT_UPSTREAM_URL = "ws://localhost:9016/feed"


class UpstreamState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class UpstreamClient:
    """WebSocket client for rugs-feed upstream service.

    Receives raw events from the rugs-feed broadcaster and passes them
    to a callback for processing by the sanitization pipeline.
    """

    def __init__(
        self,
        url: str = DEFAULT_UPSTREAM_URL,
        on_message: Callable[[dict], None] | None = None,
        max_reconnect_delay: float = 30.0,
        initial_reconnect_delay: float = 1.0,
        ping_interval: float = 20.0,
    ) -> None:
        self._url = url
        self._on_message = on_message
        self._state = UpstreamState.DISCONNECTED
        self._max_reconnect_delay = max_reconnect_delay
        self._initial_reconnect_delay = initial_reconnect_delay
        self._ping_interval = ping_interval
        self._reconnect_delay = initial_reconnect_delay
        self._ws = None
        self._stats = UpstreamStats()

    @property
    def state(self) -> UpstreamState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == UpstreamState.CONNECTED

    async def connect(self) -> None:
        """Connect to upstream with auto-reconnection.

        This method blocks until the connection is intentionally closed.
        It handles reconnection automatically on failures.
        """
        while True:
            try:
                self._state = UpstreamState.CONNECTING
                logger.info(f"Connecting to upstream: {self._url}")

                async with websockets.connect(
                    self._url,
                    ping_interval=self._ping_interval,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._state = UpstreamState.CONNECTED
                    self._reconnect_delay = self._initial_reconnect_delay
                    self._stats.connections += 1
                    logger.info(f"Connected to upstream: {self._url}")

                    await self._receive_loop(ws)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Upstream connection closed: {e}")
            except ConnectionRefusedError:
                logger.warning(f"Upstream refused connection: {self._url}")
            except OSError as e:
                logger.warning(f"Upstream connection error: {e}")
            except Exception as e:
                logger.error(f"Unexpected upstream error: {e}")
            finally:
                self._ws = None
                self._state = UpstreamState.RECONNECTING
                self._stats.disconnections += 1

            # Exponential backoff
            logger.info(f"Reconnecting in {self._reconnect_delay:.1f}s...")
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def disconnect(self) -> None:
        """Close the upstream connection."""
        if self._ws:
            await self._ws.close()
        self._state = UpstreamState.DISCONNECTED

    async def _receive_loop(self, ws) -> None:
        """Receive messages from upstream WebSocket."""
        async for message in ws:
            try:
                data = json.loads(message)
                self._stats.messages_received += 1

                if self._on_message:
                    self._on_message(data)
            except json.JSONDecodeError:
                self._stats.parse_errors += 1
                logger.warning("Failed to parse upstream message")
            except Exception as e:
                self._stats.callback_errors += 1
                logger.error(f"Message handler error: {e}")

    def get_stats(self) -> dict:
        """Return upstream client statistics."""
        return {
            "state": self._state.value,
            "url": self._url,
            "connections": self._stats.connections,
            "disconnections": self._stats.disconnections,
            "messages_received": self._stats.messages_received,
            "parse_errors": self._stats.parse_errors,
            "callback_errors": self._stats.callback_errors,
        }


class UpstreamStats:
    """Statistics for the upstream client."""

    def __init__(self) -> None:
        self.connections: int = 0
        self.disconnections: int = 0
        self.messages_received: int = 0
        self.parse_errors: int = 0
        self.callback_errors: int = 0
