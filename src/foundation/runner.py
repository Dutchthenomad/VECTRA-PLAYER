# src/foundation/runner.py
"""Foundation runner - orchestrates all components."""

import asyncio
import logging
import signal

from foundation.config import FoundationConfig
from foundation.http_server import FoundationHTTPServer
from foundation.service import FoundationService

logger = logging.getLogger(__name__)


class FoundationRunner:
    """
    Main entry point for running Foundation system.

    Orchestrates:
    - FoundationService (WebSocket broadcaster)
    - FoundationHTTPServer (monitoring UI)

    Usage:
        runner = FoundationRunner()
        await runner.start()  # Runs until interrupted
    """

    def __init__(self, config: FoundationConfig | None = None):
        self.config = config or FoundationConfig()
        self.service = FoundationService(self.config)
        self.http_server = FoundationHTTPServer(self.config)

        self._running = False
        self._tasks: list[asyncio.Task] = []

        logger.info("FoundationRunner initialized")

    async def start(self) -> None:
        """
        Start all Foundation components.

        Runs until interrupted (Ctrl+C).
        """
        self._running = True

        logger.info("Starting Foundation system...")
        logger.info(f"  WebSocket: ws://{self.config.host}:{self.config.port}/feed")
        logger.info(f"  HTTP:      http://{self.config.host}:{self.config.http_port}")

        # Start broadcaster
        broadcaster_task = asyncio.create_task(self.service.broadcaster.start())
        self._tasks.append(broadcaster_task)

        # Start HTTP server
        await self.http_server.start(
            host=self.config.host,
            port=self.config.http_port,
        )

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        logger.info("Foundation system running. Press Ctrl+C to stop.")

        # Wait for shutdown
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Stop all components gracefully."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Foundation system...")

        # Stop broadcaster
        await self.service.broadcaster.stop()

        # Cancel tasks
        for task in self._tasks:
            task.cancel()

        logger.info("Foundation system stopped")

    def get_status(self) -> dict:
        """Get combined status of all components."""
        return {
            "running": self._running,
            "service": self.service.get_status(),
            "http": {
                "port": self.config.http_port,
            },
        }

    def on_raw_event(self, raw: dict) -> None:
        """Forward raw event to service."""
        self.service.on_raw_event(raw)


def main():
    """CLI entry point."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Foundation System")
    parser.add_argument("--port", type=int, help="WebSocket port")
    parser.add_argument("--http-port", type=int, help="HTTP port")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create config with CLI overrides
    if args.port:
        os.environ["FOUNDATION_PORT"] = str(args.port)
    if args.http_port:
        os.environ["FOUNDATION_HTTP_PORT"] = str(args.http_port)

    runner = FoundationRunner()
    asyncio.run(runner.start())


if __name__ == "__main__":
    main()
