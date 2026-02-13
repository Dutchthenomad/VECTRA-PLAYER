#!/usr/bin/env python3
"""
PRNG Seed Collector for Rugs Feed Service.

Collects serverSeeds from rugs-feed for PRNG analysis.
Outputs seeds in JSONL format compatible with SEED-KRACKER.

Usage:
    python prng_collector.py
    python prng_collector.py --output seeds.jsonl
    python prng_collector.py --count 100  # Collect 100 seeds then exit
"""

import argparse
import asyncio
import json
import logging
import signal
from datetime import datetime
from pathlib import Path

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class PRNGCollector:
    """
    Collects serverSeeds from rugs-feed for PRNG analysis.

    Seeds are extracted from gameHistory on rug events and saved
    in JSONL format compatible with SEED-KRACKER and AdaptiveCracker.
    """

    def __init__(
        self,
        feed_url: str = "ws://localhost:9016/feed",
        output_path: str | None = None,
        target_count: int | None = None,
    ):
        """
        Initialize collector.

        Args:
            feed_url: WebSocket URL for rugs-feed
            output_path: Path to output JSONL file (None = stdout)
            target_count: Stop after collecting this many seeds (None = run forever)
        """
        self.feed_url = feed_url
        self.output_path = Path(output_path) if output_path else None
        self.target_count = target_count

        self.seeds_collected = 0
        self.games_seen: set[str] = set()
        self._running = False
        self._output_file = None

    async def collect(self) -> None:
        """Connect to feed and collect seeds."""
        self._running = True

        # Open output file if specified
        if self.output_path:
            self._output_file = open(self.output_path, "a")
            logger.info(f"Appending seeds to {self.output_path}")

        try:
            while self._running:
                try:
                    logger.info(f"Connecting to {self.feed_url}...")
                    async with websockets.connect(self.feed_url) as ws:
                        logger.info("Connected - collecting seeds...")
                        await self._process_events(ws)

                except websockets.exceptions.ConnectionClosed as e:
                    logger.warning(f"Connection closed: {e}")
                except Exception as e:
                    logger.error(f"Connection error: {e}")

                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

        finally:
            if self._output_file:
                self._output_file.close()

    async def _process_events(self, ws) -> None:
        """Process events looking for gameHistory with seeds."""
        async for message in ws:
            if not self._running:
                break

            event = json.loads(message)

            # Skip non-game events
            if event.get("type") == "pong":
                continue

            if event.get("event_type") != "gameStateUpdate":
                continue

            data = event.get("data", {})

            # Look for gameHistory (contains serverSeeds)
            game_history = data.get("gameHistory", [])
            if not game_history:
                continue

            # Extract seeds from gameHistory
            for game in game_history:
                await self._process_game_history_entry(game)

            # Check if we've reached target
            if self.target_count and self.seeds_collected >= self.target_count:
                logger.info(f"Reached target of {self.target_count} seeds")
                self._running = False
                break

    async def _process_game_history_entry(self, game: dict) -> None:
        """Process a single gameHistory entry."""
        game_id = game.get("id")
        if not game_id:
            return

        # Skip if already seen
        if game_id in self.games_seen:
            return
        self.games_seen.add(game_id)

        # Extract provablyFair data
        pf = game.get("provablyFair", {})
        server_seed = pf.get("serverSeed")
        server_seed_hash = pf.get("serverSeedHash")

        if not server_seed:
            return

        # Create JSONL record
        record = {
            "game_id": game_id,
            "timestamp_ms": game.get("timestamp", 0),
            "server_seed": server_seed,
            "server_seed_hash": server_seed_hash,
            "peak_multiplier": game.get("peakMultiplier", 0),
            "rugged": game.get("rugged", False),
            "game_version": game.get("gameVersion"),
            "collected_at": datetime.utcnow().isoformat(),
        }

        # Output record
        jsonl = json.dumps(record)
        if self._output_file:
            self._output_file.write(jsonl + "\n")
            self._output_file.flush()
        else:
            print(jsonl)

        self.seeds_collected += 1
        logger.info(
            f"Seed #{self.seeds_collected}: {game_id} "
            f"seed={server_seed[:16]}... "
            f"peak={record['peak_multiplier']:.2f}x"
        )

    def stop(self) -> None:
        """Stop collecting."""
        self._running = False

    def get_stats(self) -> dict:
        """Get collection statistics."""
        return {
            "seeds_collected": self.seeds_collected,
            "unique_games": len(self.games_seen),
        }


async def main():
    """Run the PRNG seed collector."""
    parser = argparse.ArgumentParser(description="PRNG Seed Collector for Rugs Feed")
    parser.add_argument(
        "--url",
        default="ws://localhost:9016/feed",
        help="WebSocket URL for rugs-feed",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSONL file (default: stdout)",
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        help="Stop after collecting this many seeds",
    )
    args = parser.parse_args()

    collector = PRNGCollector(
        feed_url=args.url,
        output_path=args.output,
        target_count=args.count,
    )

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutting down...")
        collector.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await collector.collect()
    finally:
        stats = collector.get_stats()
        logger.info(f"Final stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
