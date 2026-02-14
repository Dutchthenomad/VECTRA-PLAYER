"""WebSocket upstream consumer and downstream publisher."""

import asyncio
import json
import logging
import os

import websockets

logger = logging.getLogger(__name__)


class FeedManager:
    """Connects to upstream WebSocket and forwards processed events."""

    def __init__(self, processor):
        self.processor = processor
        self.upstream_url = os.getenv("UPSTREAM_URL", "ws://localhost:9000/feed")
        self._ws = None
        self._running = False

    async def connect(self):
        self._running = True
        while self._running:
            try:
                async with websockets.connect(self.upstream_url) as ws:
                    self._ws = ws
                    logger.info("Connected to upstream: %s", self.upstream_url)
                    async for message in ws:
                        data = json.loads(message)
                        await self.processor.process(data)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Upstream connection closed, reconnecting...")
            except Exception:
                logger.exception("Upstream connection error")
            if self._running:
                await asyncio.sleep(2.0)

    async def disconnect(self):
        self._running = False
        if self._ws:
            await self._ws.close()
