#!/usr/bin/env python3
"""
Live gameHistory Capture - Validates structure by capturing next rug event

Connects to live rugs.fun feed and captures the gameHistory array when
the next game rugs. Saves to JSON for analysis.

Usage:
    cd /home/devops/Desktop/VECTRA-PLAYER
    .venv/bin/python scripts/capture_live_gamehistory.py
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from browser.bridge import BrowserBridge, BridgeStatus
from services.event_bus import event_bus, Events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GameHistoryValidator:
    """Captures and validates gameHistory structure from live feed"""

    def __init__(self, output_file: Path):
        self.output_file = output_file
        self.bridge = None
        self.captured = False
        self._shutdown = False

    def _on_ws_event(self, wrapped: dict):
        """Handle WebSocket events - look for gameStateUpdate with gameHistory"""
        try:
            data = wrapped.get("data", {})
            event_name = data.get("event")
            event_data = data.get("data", {})

            if event_name == "gameStateUpdate":
                game_history = event_data.get("gameHistory", [])

                if game_history and not self.captured:
                    # Found it! This is a rug event with complete game data
                    logger.info("=" * 70)
                    logger.info("🎯 CAPTURED gameHistory from rug event!")
                    logger.info(f"   Games in history: {len(game_history)}")
                    logger.info("=" * 70)

                    # Save to file
                    output_data = {
                        "capture_timestamp": datetime.utcnow().isoformat(),
                        "current_game_id": event_data.get("gameId"),
                        "game_history_count": len(game_history),
                        "gameHistory": game_history,
                    }

                    with open(self.output_file, "w") as f:
                        json.dump(output_data, f, indent=2, default=str)

                    logger.info(f"✅ Saved to: {self.output_file}")
                    logger.info("")

                    # Analyze structure
                    self._analyze_structure(game_history)

                    self.captured = True
                    logger.info("\n✨ Capture complete! Press Ctrl+C to exit.")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    def _analyze_structure(self, game_history: list):
        """Analyze the captured gameHistory structure"""
        logger.info("\n📊 Structure Analysis:")
        logger.info("-" * 70)

        if not game_history:
            logger.warning("No games in gameHistory!")
            return

        # Analyze first game
        first_game = game_history[0]
        logger.info(f"\nFirst game (index 0):")
        logger.info(f"  Game ID: {first_game.get('id')}")
        logger.info(f"  Timestamp: {first_game.get('timestamp')}")
        logger.info(f"  Rugged: {first_game.get('rugged')}")
        logger.info(f"  Peak Multiplier: {first_game.get('peakMultiplier')}")

        # Check globalSideBets
        global_sidebets = first_game.get("globalSideBets", [])
        logger.info(f"  globalSideBets: {len(global_sidebets)} sidebets found")

        if global_sidebets:
            logger.info(f"\n  Sample sidebet:")
            sample = global_sidebets[0]
            logger.info(f"    Player: {sample.get('username', 'N/A')}")
            logger.info(f"    Target: {sample.get('target')}x")
            logger.info(f"    Bet Size: {sample.get('betSize')} SOL")
            logger.info(f"    Start Tick: {sample.get('startTick')}")
            logger.info(f"    End Tick: {sample.get('endTick')}")

            # Check if we can determine win/loss
            peak = first_game.get("peakMultiplier", 0)
            target = sample.get("target", 0)
            won = peak >= target if peak and target else None
            if won is not None:
                logger.info(f"    Outcome: {'✅ WON' if won else '❌ LOST'} (peak: {peak}x, target: {target}x)")

        # Check prices array
        prices = first_game.get("prices", [])
        logger.info(f"  prices: {len(prices)} ticks")
        if prices:
            logger.info(f"    First tick: {prices[0]}")
            logger.info(f"    Last tick: {prices[-1]}")
            logger.info(f"    Peak: {max(prices) if prices else 'N/A'}")

        # Summary for all games
        logger.info(f"\n📈 Summary across all {len(game_history)} games:")
        total_sidebets = sum(len(g.get("globalSideBets", [])) for g in game_history)
        total_ticks = sum(len(g.get("prices", [])) for g in game_history)
        logger.info(f"  Total sidebets: {total_sidebets}")
        logger.info(f"  Total ticks: {total_ticks}")
        logger.info(f"  Avg ticks per game: {total_ticks / len(game_history):.1f}")

        logger.info("-" * 70)

    def _on_status_change(self, status: BridgeStatus):
        """Handle bridge status changes"""
        logger.info(f"Bridge status: {status.value}")

        if status == BridgeStatus.CONNECTED:
            logger.info("=" * 70)
            logger.info("🔗 CONNECTED TO LIVE FEED")
            logger.info("   Waiting for next rug event...")
            logger.info("   (This may take a few minutes)")
            logger.info("=" * 70)

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        logger.info("\n\n🛑 Shutting down...")
        self._shutdown = True
        if self.bridge:
            self.bridge.disconnect()
        sys.exit(0)

    def run(self):
        """Run the capture session"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("=" * 70)
        logger.info("🎮 Live gameHistory Validator")
        logger.info("=" * 70)
        logger.info(f"Output: {self.output_file}")
        logger.info("")

        # Start event bus
        event_bus.start()

        # Subscribe to WebSocket events
        event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_event, weak=False)

        # Create and connect bridge
        self.bridge = BrowserBridge()
        self.bridge.on_status_change = self._on_status_change

        try:
            # Connect to browser (blocking)
            self.bridge.connect()

            # Keep alive until captured or interrupted
            while not self.captured and not self._shutdown:
                import time
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n🛑 Interrupted by user")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            if self.bridge:
                self.bridge.disconnect()
            event_bus.stop()


if __name__ == "__main__":
    output_file = Path("/home/devops/Desktop/claude-flow/knowledge/rugipedia/raw-data/gameHistory-live-capture.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    validator = GameHistoryValidator(output_file)
    validator.run()
