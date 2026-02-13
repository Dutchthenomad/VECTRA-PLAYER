#!/usr/bin/env python3
"""
Sample Subscriber for Rugs Feed Service.

Demonstrates how to connect to the rugs-feed WebSocket broadcaster
and process events from rugs.fun in real-time.

Usage:
    python sample_subscriber.py
    python sample_subscriber.py --url ws://localhost:9016/feed
    python sample_subscriber.py --verbose
"""

import argparse
import asyncio
import json
import logging
import signal
from dataclasses import dataclass
from datetime import datetime

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Tracks current game state."""

    game_id: str | None = None
    tick_count: int = 0
    price: float = 1.0
    peak_price: float = 1.0
    rugged: bool = False
    active: bool = False


class SampleSubscriber:
    """
    Sample subscriber that connects to rugs-feed and processes events.

    This demonstrates the basic pattern for consuming the feed.
    Extend this class to add your own processing logic.
    """

    def __init__(self, feed_url: str = "ws://localhost:9016/feed", verbose: bool = False):
        """
        Initialize subscriber.

        Args:
            feed_url: WebSocket URL for rugs-feed
            verbose: Whether to log all events
        """
        self.feed_url = feed_url
        self.verbose = verbose
        self.state = GameState()
        self.events_received = 0
        self.games_seen = 0
        self._running = False

    async def connect(self) -> None:
        """Connect to the feed and process events."""
        self._running = True

        while self._running:
            try:
                logger.info(f"Connecting to {self.feed_url}...")
                async with websockets.connect(self.feed_url) as ws:
                    logger.info("Connected to rugs-feed")
                    await self._process_events(ws)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}")
            except Exception as e:
                logger.error(f"Connection error: {e}")

            if self._running:
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _process_events(self, ws) -> None:
        """Process events from the WebSocket."""
        # Start keepalive task
        keepalive_task = asyncio.create_task(self._keepalive(ws))

        try:
            async for message in ws:
                if not self._running:
                    break

                event = json.loads(message)
                self.events_received += 1

                # Skip pong messages
                if event.get("type") == "pong":
                    continue

                await self._handle_event(event)

        finally:
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass

    async def _keepalive(self, ws) -> None:
        """Send periodic pings to keep connection alive."""
        while True:
            try:
                await asyncio.sleep(30)
                ping = {"action": "ping", "ts": datetime.utcnow().timestamp()}
                await ws.send(json.dumps(ping))
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def _handle_event(self, event: dict) -> None:
        """
        Handle a single event from the feed.

        Override this method to add custom processing logic.

        Args:
            event: Event dict with type, event_type, data, timestamp, game_id
        """
        event_type = event.get("event_type")
        data = event.get("data", {})
        game_id = event.get("game_id")

        if self.verbose:
            logger.debug(f"Event: {event_type} game={game_id}")

        # Handle different event types
        if event_type == "gameStateUpdate":
            await self._handle_game_state(data, game_id)

        elif event_type == "standard/newTrade":
            await self._handle_trade(data)

        elif event_type == "currentSidebet":
            await self._handle_sidebet(data)

        elif event_type == "playerUpdate":
            await self._handle_player_update(data)

    async def _handle_game_state(self, data: dict, game_id: str | None) -> None:
        """Handle gameStateUpdate event."""
        # Track new games
        if game_id and game_id != self.state.game_id:
            if self.state.game_id:
                logger.info(
                    f"Game ended: {self.state.game_id} "
                    f"peak={self.state.peak_price:.2f}x "
                    f"ticks={self.state.tick_count}"
                )
            self.state = GameState(game_id=game_id)
            self.games_seen += 1
            logger.info(f"New game: {game_id}")

        # Update state
        self.state.tick_count = data.get("tickCount", 0)
        self.state.price = data.get("price", 1.0)
        self.state.peak_price = max(self.state.peak_price, self.state.price)
        self.state.rugged = data.get("rugged", False)
        self.state.active = data.get("active", False)

        # Log significant events
        if self.state.rugged and not self.state.active:
            logger.info(
                f"RUGGED! game={game_id} "
                f"peak={self.state.peak_price:.2f}x "
                f"final={self.state.price:.4f}x "
                f"ticks={self.state.tick_count}"
            )

            # Check for gameHistory (contains serverSeeds!)
            game_history = data.get("gameHistory", [])
            if game_history:
                logger.info(f"  gameHistory: {len(game_history)} games available")
                # First entry has the most recent serverSeed
                first = game_history[0]
                pf = first.get("provablyFair", {})
                seed = pf.get("serverSeed", "")
                if seed:
                    logger.info(f"  serverSeed: {seed[:16]}...")

        elif self.verbose and self.state.tick_count % 50 == 0:
            logger.info(
                f"Tick {self.state.tick_count}: "
                f"price={self.state.price:.4f}x "
                f"peak={self.state.peak_price:.2f}x"
            )

    async def _handle_trade(self, data: dict) -> None:
        """Handle standard/newTrade event."""
        username = data.get("username", "unknown")
        action = data.get("action", "")
        amount = data.get("amount", 0)

        if self.verbose:
            logger.info(f"Trade: {username} {action} {amount}")

    async def _handle_sidebet(self, data: dict) -> None:
        """Handle currentSidebet event."""
        username = data.get("username", "unknown")
        bet_amount = data.get("betAmount", 0)
        x_payout = data.get("xPayout", 0)

        if self.verbose:
            logger.info(f"Sidebet: {username} bet {bet_amount} for {x_payout}x")

    async def _handle_player_update(self, data: dict) -> None:
        """Handle playerUpdate event."""
        if self.verbose:
            balance = data.get("balance", 0)
            logger.info(f"Player update: balance={balance}")

    def stop(self) -> None:
        """Stop the subscriber."""
        self._running = False

    def get_stats(self) -> dict:
        """Get subscriber statistics."""
        return {
            "events_received": self.events_received,
            "games_seen": self.games_seen,
            "current_game": self.state.game_id,
            "current_tick": self.state.tick_count,
            "current_price": self.state.price,
        }


async def main():
    """Run the sample subscriber."""
    parser = argparse.ArgumentParser(description="Sample Rugs Feed Subscriber")
    parser.add_argument(
        "--url",
        default="ws://localhost:9016/feed",
        help="WebSocket URL for rugs-feed",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log all events",
    )
    args = parser.parse_args()

    subscriber = SampleSubscriber(feed_url=args.url, verbose=args.verbose)

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutting down...")
        subscriber.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await subscriber.connect()
    finally:
        stats = subscriber.get_stats()
        logger.info(f"Final stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
