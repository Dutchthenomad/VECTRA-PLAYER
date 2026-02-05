"""
Rugs Feed Service Main Entry Point

Starts:
- Direct Socket.IO connection to rugs.fun
- SQLite storage for event capture
- FastAPI server for querying captured data

Usage:
    python -m src.main
"""

import asyncio
import logging
import os
import signal
from pathlib import Path

import uvicorn
import yaml

from .api import create_app
from .client import CapturedEvent, RugsFeedClient
from .storage import EventStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from file and environment."""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    defaults = {
        "rugs_backend_url": "https://backend.rugs.fun",
        "storage_path": "/data/rugs_feed.db",
        "port": 9016,
        "host": "0.0.0.0",
        "max_reconnect_attempts": 100,
        "reconnect_delay_seconds": 5,
        "log_level": "INFO",
    }

    # Load from config file
    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
            defaults.update(file_config)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    # Override with environment variables
    env_mappings = {
        "RUGS_BACKEND_URL": "rugs_backend_url",
        "STORAGE_PATH": "storage_path",
        "PORT": "port",
        "HOST": "host",
        "LOG_LEVEL": "log_level",
    }

    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key)
        if value:
            if config_key == "port":
                defaults[config_key] = int(value)
            else:
                defaults[config_key] = value

    return defaults


# Global references for cleanup
_client: RugsFeedClient | None = None
_storage: EventStorage | None = None
_background_tasks: set = set()


async def run_service():
    """Run the Rugs Feed Service."""
    global _client, _storage

    config = load_config()

    # Set log level
    logging.getLogger().setLevel(config["log_level"])

    logger.info("=" * 60)
    logger.info("Rugs Feed Service Starting")
    logger.info("=" * 60)
    logger.info(f"Backend URL: {config['rugs_backend_url']}")
    logger.info(f"Storage Path: {config['storage_path']}")
    logger.info(f"API Port: {config['port']}")

    # Initialize storage
    _storage = EventStorage(config["storage_path"])
    await _storage.initialize()

    # Event handler that stores to SQLite
    def on_event(event: CapturedEvent):
        task = asyncio.create_task(_storage.store_event(event))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    # Initialize client
    _client = RugsFeedClient(
        url=config["rugs_backend_url"],
        on_event=on_event,
    )

    # Create API app
    app = create_app(
        db_path=config["storage_path"],
        auto_connect=False,  # We manage connection separately
    )

    # Shutdown handler
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start API server
    uvicorn_config = uvicorn.Config(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    async def run_api():
        await server.serve()

    async def run_websocket():
        """Maintain WebSocket connection with reconnection."""
        while not shutdown_event.is_set():
            try:
                logger.info("Connecting to rugs.fun backend...")
                await _client.connect()
                await _client.wait()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            if not shutdown_event.is_set():
                delay = config["reconnect_delay_seconds"]
                logger.info(f"Reconnecting in {delay}s...")
                await asyncio.sleep(delay)

    async def periodic_stats():
        """Log statistics periodically."""
        while not shutdown_event.is_set():
            try:
                stats = await _storage.get_stats()
                logger.info(
                    f"Stats: {stats['total_games']} games, "
                    f"{stats['seed_reveals']} seeds, "
                    f"{stats['total_events']} events"
                )
            except Exception as e:
                logger.error(f"Stats error: {e}")
            await asyncio.sleep(300)  # Every 5 minutes

    try:
        await asyncio.gather(
            run_api(),
            run_websocket(),
            periodic_stats(),
        )
    except asyncio.CancelledError:
        logger.info("Service tasks cancelled")
    finally:
        logger.info("Cleaning up...")
        if _client:
            await _client.disconnect()
        if _storage:
            await _storage.close()
        logger.info("Rugs Feed Service stopped")


if __name__ == "__main__":
    asyncio.run(run_service())
