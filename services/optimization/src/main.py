"""
Optimization Service Main Entry Point

Starts the Optimization Service with:
- FoundationClient for WebSocket event streaming
- OptimizationSubscriber for game analysis
- FastAPI server for API access

Usage:
    python -m src.main
    # or
    uvicorn src.main:app --host 0.0.0.0 --port 9020
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

# Add project root to path for foundation imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from .api import create_app
from .profiles.producer import ProfileProducer
from .subscriber import OptimizationSubscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from file and environment."""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    defaults = {
        "foundation_ws_url": "ws://localhost:9000/feed",
        "storage_path": str(Path.home() / "rugs_data" / "strategy_profiles"),
        "port": 9020,
        "host": "0.0.0.0",
        "monte_carlo_iterations": 10000,
        "kelly_fraction": 0.25,
        "min_games_for_profile": 50,
    }

    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
            defaults.update(file_config)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    # Environment overrides
    env_mappings = {
        "FOUNDATION_WS_URL": "foundation_ws_url",
        "STORAGE_PATH": "storage_path",
        "OPTIMIZATION_SERVICE_PORT": "port",
        "HOST": "host",
        "MONTE_CARLO_ITERATIONS": "monte_carlo_iterations",
        "KELLY_FRACTION": "kelly_fraction",
    }

    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key)
        if value is not None:
            if config_key in ("port", "monte_carlo_iterations"):
                defaults[config_key] = int(value)
            elif config_key == "kelly_fraction":
                defaults[config_key] = float(value)
            else:
                defaults[config_key] = value

    return defaults


# Global references for cleanup
_subscriber: OptimizationSubscriber | None = None
_shutdown_event: asyncio.Event | None = None


async def run_service():
    """Run the Optimization Service."""
    global _subscriber, _shutdown_event

    config = load_config()
    start_time = datetime.utcnow()

    logger.info("=" * 60)
    logger.info("Optimization Service Starting")
    logger.info("=" * 60)
    logger.info(f"Foundation URL: {config['foundation_ws_url']}")
    logger.info(f"API Port: {config['port']}")
    logger.info(f"Monte Carlo Iterations: {config['monte_carlo_iterations']}")

    # Initialize components
    producer = ProfileProducer(
        kelly_fraction=config["kelly_fraction"],
        monte_carlo_iterations=config["monte_carlo_iterations"],
    )

    # Create a mock client for standalone mode (no Foundation connection)
    class StandaloneClient:
        """Mock client for standalone operation."""

        def __init__(self):
            self._handlers = {}

        def on(self, event: str, handler):
            """Register event handler."""
            self._handlers[event] = handler
            return lambda: self._handlers.pop(event, None)

    client = StandaloneClient()
    _subscriber = OptimizationSubscriber(
        client=client,
        producer=producer,
        min_games_for_profile=config["min_games_for_profile"],
    )

    # Create API app
    app = create_app(
        subscriber=_subscriber,
        config_path=Path(__file__).parent.parent / "config",
        start_time=start_time,
    )

    # Setup shutdown handler
    _shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        if _shutdown_event:
            _shutdown_event.set()

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

    try:
        await server.serve()
    except asyncio.CancelledError:
        logger.info("Service cancelled")
    finally:
        logger.info("Optimization Service stopped")


def create_standalone_app():
    """Create app for direct uvicorn usage."""
    config = load_config()
    start_time = datetime.utcnow()

    producer = ProfileProducer(
        kelly_fraction=config["kelly_fraction"],
        monte_carlo_iterations=config["monte_carlo_iterations"],
    )

    # Standalone mode with mock client
    class StandaloneClient:
        def __init__(self):
            self._handlers = {}

        def on(self, event: str, handler):
            self._handlers[event] = handler
            return lambda: self._handlers.pop(event, None)

    client = StandaloneClient()
    subscriber = OptimizationSubscriber(
        client=client,
        producer=producer,
        min_games_for_profile=config["min_games_for_profile"],
    )

    return create_app(
        subscriber=subscriber,
        config_path=Path(__file__).parent.parent / "config",
        start_time=start_time,
    )


# For uvicorn direct usage: uvicorn src.main:app
app = create_standalone_app()


if __name__ == "__main__":
    asyncio.run(run_service())
