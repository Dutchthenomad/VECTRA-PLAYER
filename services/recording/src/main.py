"""
Recording Service Main Entry Point

Starts the Recording Service with:
- FoundationClient for WebSocket event streaming
- RecordingSubscriber for gameHistory extraction
- FastAPI server for control and monitoring

Usage:
    python -m src.main
    # or
    uvicorn src.main:app --host 0.0.0.0 --port 9010
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
import yaml

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from foundation.client import FoundationClient

from .api import create_app
from .dedup import DeduplicationTracker
from .storage import GameStorage
from .subscriber import RecordingSubscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """
    Load configuration from config file and environment.

    Priority: Environment variables > config file > defaults
    """
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    defaults = {
        "foundation_ws_url": "ws://localhost:9000/feed",
        "storage_path": str(Path.home() / "rugs_recordings" / "raw_captures"),
        "dedup_path": str(Path(__file__).parent.parent / "config" / "seen_games.json"),
        "port": 9010,
        "host": "0.0.0.0",
        "auto_start_recording": True,
    }

    # Load from config file
    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
            defaults.update(file_config)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")

    # Override with environment variables
    env_mappings = {
        "FOUNDATION_WS_URL": "foundation_ws_url",
        "STORAGE_PATH": "storage_path",
        "DEDUP_PATH": "dedup_path",
        "PORT": "port",
        "HOST": "host",
        "AUTO_START_RECORDING": "auto_start_recording",
    }

    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key)
        if value is not None:
            # Handle boolean conversion
            if config_key == "auto_start_recording":
                defaults[config_key] = value.lower() in ("true", "1", "yes")
            elif config_key == "port":
                defaults[config_key] = int(value)
            else:
                defaults[config_key] = value

    return defaults


# Global references for cleanup
_subscriber: RecordingSubscriber | None = None
_client: FoundationClient | None = None


async def run_service():
    """
    Run the Recording Service.

    Starts the WebSocket client and maintains connection.
    """
    global _subscriber, _client

    config = load_config()
    start_time = datetime.utcnow()

    logger.info("=" * 60)
    logger.info("Recording Service Starting")
    logger.info("=" * 60)
    logger.info(f"Foundation URL: {config['foundation_ws_url']}")
    logger.info(f"Storage Path: {config['storage_path']}")
    logger.info(f"API Port: {config['port']}")
    logger.info(f"Auto-start Recording: {config['auto_start_recording']}")

    # Initialize components
    storage = GameStorage(config["storage_path"])
    dedup = DeduplicationTracker(
        persist_path=config["dedup_path"],
        max_cache_size=10000,
    )

    _client = FoundationClient(url=config["foundation_ws_url"])
    _subscriber = RecordingSubscriber(
        client=_client,
        storage=storage,
        dedup_tracker=dedup,
    )

    # Set initial recording state
    if not config["auto_start_recording"]:
        _subscriber.stop_recording()

    # Create API app
    app = create_app(
        subscriber=_subscriber,
        config_path=Path(__file__).parent.parent / "config",
        start_time=start_time,
    )

    # Setup shutdown handler
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start API server in background
    uvicorn_config = uvicorn.Config(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    # Run server and Foundation client concurrently
    async def run_api():
        await server.serve()

    async def run_foundation():
        while not shutdown_event.is_set():
            try:
                await _client.connect()
            except Exception as e:
                logger.error(f"Foundation connection error: {e}")
            if not shutdown_event.is_set():
                await asyncio.sleep(5)  # Reconnect delay

    async def periodic_tasks():
        """Periodic maintenance tasks."""
        while not shutdown_event.is_set():
            try:
                # Persist dedup state
                dedup.persist()
                # Flush storage buffer
                storage.flush()
            except Exception as e:
                logger.error(f"Periodic task error: {e}")
            await asyncio.sleep(30)  # Every 30 seconds

    try:
        await asyncio.gather(
            run_api(),
            run_foundation(),
            periodic_tasks(),
        )
    except asyncio.CancelledError:
        logger.info("Service tasks cancelled")
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        if _client:
            await _client.disconnect()
        if dedup:
            dedup.persist()
        if storage:
            storage.flush()
        logger.info("Recording Service stopped")


# Create app instance for uvicorn direct usage
def create_standalone_app():
    """Create app for running with uvicorn directly."""
    config = load_config()
    start_time = datetime.utcnow()

    storage = GameStorage(config["storage_path"])
    dedup = DeduplicationTracker(
        persist_path=config["dedup_path"],
        max_cache_size=10000,
    )

    # For standalone mode, we need to handle Foundation connection differently
    # The subscriber will be created when the Foundation client connects
    class StandaloneSubscriber:
        """Placeholder subscriber for standalone API mode."""

        def __init__(self):
            self._connected = False
            self._stats = type(
                "Stats",
                (),
                {
                    "is_recording": True,
                    "session_games": 0,
                    "today_games": storage.get_today_game_count(),
                    "total_games": storage.get_total_game_count(),
                    "deduped_count": 0,
                    "last_rug_multiplier": None,
                    "last_rug_time": None,
                    "session_start": start_time,
                },
            )()
            self._storage = storage

        @property
        def stats(self):
            return self._stats

        @property
        def is_recording(self):
            return self._stats.is_recording

        def start_recording(self):
            self._stats.is_recording = True
            return True

        def stop_recording(self):
            self._stats.is_recording = False
            return True

        def get_recent_games(self, limit=10):
            return storage.get_recent_games(limit)

    subscriber = StandaloneSubscriber()

    return create_app(
        subscriber=subscriber,
        config_path=Path(__file__).parent.parent / "config",
        start_time=start_time,
    )


# For uvicorn direct usage: uvicorn src.main:app
app = create_standalone_app()


if __name__ == "__main__":
    asyncio.run(run_service())
