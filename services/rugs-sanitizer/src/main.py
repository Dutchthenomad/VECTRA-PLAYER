"""
Rugs Sanitizer Service Main Entry Point.

Starts:
- Upstream WebSocket client (connects to rugs-feed :9016)
- Sanitization pipeline (phase detection, validation, annotation)
- Multi-channel WebSocket broadcaster
- Smart history collector
- FastAPI server (health, stats, channel WebSocket endpoints)

Usage:
    python -m src.main
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

import uvicorn
import yaml

from .api import create_app
from .broadcaster import ChannelBroadcaster
from .history_collector import HistoryCollector
from .models import Channel, Phase, SanitizedEvent
from .sanitizer import SanitizationPipeline
from .upstream import UpstreamClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from file and environment."""
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    defaults = {
        "upstream_url": "ws://localhost:9016/feed",
        "port": 9017,
        "host": "0.0.0.0",
        "log_level": "INFO",
        "history_collection_interval": 10,
    }

    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
            defaults.update(file_config)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    env_mappings = {
        "UPSTREAM_URL": "upstream_url",
        "PORT": "port",
        "HOST": "host",
        "LOG_LEVEL": "log_level",
        "HISTORY_COLLECTION_INTERVAL": "history_collection_interval",
    }

    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key)
        if value:
            if config_key in ("port", "history_collection_interval"):
                defaults[config_key] = int(value)
            else:
                defaults[config_key] = value

    return defaults


async def run_service():
    """Run the Rugs Sanitizer Service."""
    config = load_config()
    logging.getLogger().setLevel(config["log_level"])

    logger.info("=" * 60)
    logger.info("Rugs Sanitizer Service Starting")
    logger.info("=" * 60)
    logger.info(f"Upstream URL: {config['upstream_url']}")
    logger.info(f"API Port: {config['port']}")
    logger.info(f"History collection interval: every {config['history_collection_interval']} rugs")
    logger.info("Channels: /feed/game, /feed/stats, /feed/trades, /feed/history, /feed/all")

    # Initialize components
    pipeline = SanitizationPipeline()
    broadcaster = ChannelBroadcaster()
    history_collector = HistoryCollector(collection_interval=config["history_collection_interval"])

    # Wire pipeline -> broadcaster
    def on_sanitized_event(event: SanitizedEvent) -> None:
        broadcaster.broadcast(event)

    for channel in Channel:
        if channel != Channel.ALL:
            pipeline.on_event(channel, on_sanitized_event)

    # Wire pipeline -> history collector (on rug detection)
    # Track last rug game ID to avoid calling on_rug() multiple times per game.
    # Multiple RUGGED-phase ticks fire per game (the rug broadcasts on several
    # consecutive ticks), but we should only count each game once.
    last_rug_game_id: str = ""

    def on_game_event(event: SanitizedEvent) -> None:
        nonlocal last_rug_game_id
        if event.phase == Phase.RUGGED:
            game_id = event.game_id
            if game_id == last_rug_game_id:
                return  # Already processed this rug
            last_rug_game_id = game_id

            game_data = event.data
            game_history_raw = game_data.get("game_history")
            has_gc = game_data.get("has_god_candle", False)
            history_collector.on_rug(game_history_raw, has_god_candle=has_gc)

    pipeline.on_event(Channel.GAME, on_game_event)

    # Upstream message handler
    def on_upstream_message(raw: dict) -> None:
        pipeline.process_raw(raw)

    upstream = UpstreamClient(
        url=config["upstream_url"],
        on_message=on_upstream_message,
    )

    # Start broadcaster
    broadcaster.start()

    # Create API
    app = create_app(
        pipeline=pipeline,
        broadcaster=broadcaster,
        upstream=upstream,
        history_collector=history_collector,
    )

    # Shutdown handling
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    uvicorn_config = uvicorn.Config(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    async def run_api():
        await server.serve()

    async def run_upstream():
        while not shutdown_event.is_set():
            try:
                await upstream.connect()
            except Exception as e:
                logger.error(f"Upstream error: {e}")
            if not shutdown_event.is_set():
                await asyncio.sleep(5)

    async def periodic_stats():
        while not shutdown_event.is_set():
            try:
                p_stats = pipeline.get_stats()
                b_stats = broadcaster.get_stats()
                u_stats = upstream.get_stats()
                h_stats = history_collector.get_stats()
                logger.info(
                    f"Stats: {p_stats['events_received']} events processed, "
                    f"{p_stats['game_events']} game, "
                    f"{p_stats['trade_events']} trades, "
                    f"{h_stats['records_collected']} history records, "
                    f"{b_stats['channels']['all']['clients']} ws clients, "
                    f"upstream={u_stats['state']}"
                )
            except Exception as e:
                logger.error(f"Stats error: {e}")
            await asyncio.sleep(300)

    try:
        await broadcaster.start_broadcast_loop()
        await asyncio.gather(
            run_api(),
            run_upstream(),
            periodic_stats(),
        )
    except asyncio.CancelledError:
        logger.info("Service tasks cancelled")
    finally:
        logger.info("Cleaning up...")
        broadcaster.stop()
        await upstream.disconnect()
        logger.info("Rugs Sanitizer Service stopped")


if __name__ == "__main__":
    asyncio.run(run_service())
