"""
Bayesian Predictor Subscriber - Integrates with Foundation WebSocket framework.

This is the main entry point that:
1. Subscribes to the WebSocket feed via Foundation client
2. Feeds events to the prediction engine
3. Starts the HTTP API for the UI

Usage:
    python -m bayesian_predictor.subscriber

Or if using the Foundation framework:
    # In your subscriber registration
    from bayesian_predictor.subscriber import BayesianPredictorSubscriber
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from prediction_engine import LivePredictionEngine, start_api_server

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("bayesian_predictor")


class BayesianPredictorSubscriber:
    """
    Subscriber that feeds WebSocket events to the prediction engine.

    Can be used standalone or integrated with the Foundation framework.
    """

    def __init__(
        self,
        ws_url: str = "ws://localhost:9000/feed",
        api_port: int = 9001,
        prediction_tick: int = 5,
    ):
        """
        Initialize the subscriber.

        Args:
            ws_url: WebSocket URL to connect to
            api_port: Port for the prediction API server
            prediction_tick: Make prediction by this tick (default: 5)
        """
        self.ws_url = ws_url
        self.api_port = api_port

        # Initialize prediction engine
        self.engine = LivePredictionEngine(prediction_tick_threshold=prediction_tick)

        # WebSocket connection
        self.ws = None
        self.connected = False
        self.should_run = True

        # Stats
        self.messages_received = 0
        self.last_game_id = None

    async def connect(self):
        """Connect to WebSocket and start processing"""
        import websockets

        logger.info(f"Connecting to {self.ws_url}...")

        while self.should_run:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws = ws
                    self.connected = True
                    logger.info("✓ Connected to WebSocket")

                    async for message in ws:
                        if not self.should_run:
                            break
                        await self._handle_message(message)

            except Exception as e:
                self.connected = False
                logger.warning(f"WebSocket error: {e}. Reconnecting in 2s...")
                await asyncio.sleep(2)

    async def _handle_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            event = json.loads(message)
            self.messages_received += 1

            # Feed to prediction engine
            self.engine.process_event(event)

            # Track game transitions for logging
            game_id = event.get("gameId")
            if game_id and game_id != self.last_game_id:
                self.last_game_id = game_id

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def stop(self):
        """Stop the subscriber"""
        self.should_run = False
        logger.info("Stopping subscriber...")


async def run_standalone(ws_url: str = "ws://localhost:9000/feed", api_port: int = 9001):
    """
    Run the predictor as a standalone process.

    Connects to WebSocket, starts API server, and processes events.
    """
    subscriber = BayesianPredictorSubscriber(ws_url=ws_url, api_port=api_port, prediction_tick=5)

    # Start API server
    start_api_server(subscriber.engine, port=api_port)

    # Handle shutdown
    def shutdown(sig, frame):
        logger.info(f"Received {sig}, shutting down...")
        subscriber.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("\n" + "=" * 60)
    print("  BAYESIAN PREDICTOR")
    print("=" * 60)
    print(f"  WebSocket: {ws_url}")
    print(f"  API:       http://localhost:{api_port}/state")
    print("  UI:        Open ui/index.html in browser")
    print("=" * 60)
    print("  Waiting for games...\n")

    # Connect and run
    await subscriber.connect()


# === Foundation Framework Integration ===
# If using the Foundation subscriber framework, implement these

try:
    from foundation.events import GameTickEvent
    from foundation.subscriber import BaseSubscriber

    class FoundationBayesianSubscriber(BaseSubscriber):
        """
        Foundation framework compatible subscriber.

        Register with:
            client = FoundationClient(url="ws://localhost:9000/feed")
            subscriber = FoundationBayesianSubscriber(client)
            await client.connect()
        """

        def __init__(self, client, api_port: int = 9001):
            super().__init__(client)
            self.engine = LivePredictionEngine(prediction_tick_threshold=5)
            start_api_server(self.engine, port=api_port)
            logger.info(f"Foundation subscriber initialized, API on port {api_port}")

        def on_game_tick(self, event: GameTickEvent) -> None:
            """Handle game tick events"""
            # Convert Foundation event to dict format
            event_dict = {
                "type": "game.tick",
                "gameId": event.game_id,
                "data": {
                    "tick": event.tick_count,
                    "price": event.price,
                    "active": event.active,
                    "rugged": event.rugged,
                    "cooldownTimer": event.cooldown_timer,
                    "allowPreRoundBuys": getattr(event, "allow_pre_round_buys", False),
                    "gameHistory": getattr(event, "game_history", []),
                },
            }
            self.engine.process_event(event_dict)

        def on_player_state(self, event) -> None:
            """Handle player state (not used for predictions)"""
            pass

        def on_connection_change(self, connected: bool) -> None:
            """Handle connection changes"""
            logger.info(f"Foundation connection: {'connected' if connected else 'disconnected'}")

except ImportError:
    # Foundation framework not available
    FoundationBayesianSubscriber = None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bayesian Predictor for rugs.fun")
    parser.add_argument(
        "--ws-url",
        default="ws://localhost:9000/feed",
        help="WebSocket URL (default: ws://localhost:9000/feed)",
    )
    parser.add_argument(
        "--api-port", type=int, default=9001, help="API server port (default: 9001)"
    )
    args = parser.parse_args()

    asyncio.run(run_standalone(ws_url=args.ws_url, api_port=args.api_port))
