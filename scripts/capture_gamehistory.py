#!/usr/bin/env python3
"""
gameHistory Capture Script - Uses VECTRA-PLAYER's Browser Bridge

This script uses VECTRA-PLAYER's existing CDP infrastructure to capture
gameHistory events for CANONICAL verification.

Usage:
    # Launch Chrome first:
    google-chrome --remote-debugging-port=9222 https://rugs.fun

    # Then run capture:
    cd /home/nomad/Desktop/VECTRA-PLAYER
    .venv/bin/python scripts/capture_gamehistory.py --min-rugs 4

Output:
    ~/rugs_data/gamehistory_captures/YYYYMMDD_HHMMSS/
    ├── rug_events/           # Rug emission pairs
    ├── trades/               # Live newTrade events
    ├── sidebets/             # Live newSideBet events
    └── capture_manifest.json # Session summary
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from browser.bridge import BrowserBridge, BridgeStatus
from services.event_bus import event_bus
from services.game_history_capture import GameHistoryCaptureService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CaptureRunner:
    """Orchestrates browser connection and capture."""

    def __init__(self, target_rugs: int = 4, output_dir: Path | None = None):
        self.target_rugs = target_rugs
        self.output_dir = output_dir

        # Components
        self.bridge = None
        self.capture_service = None
        self._shutdown_requested = False

    def _on_status_change(self, status: BridgeStatus):
        """Handle bridge status changes."""
        logger.info(f"Bridge status: {status.value}")

        if status == BridgeStatus.CONNECTED:
            logger.info("=" * 60)
            logger.info("CONNECTED TO BROWSER - CAPTURE ACTIVE")
            logger.info(f"Target: {self.target_rugs} rug event pairs")
            logger.info("Press Ctrl+C to stop capture")
            logger.info("=" * 60)

        elif status == BridgeStatus.ERROR:
            logger.error("Bridge connection failed!")

    def run(self):
        """Run the capture session."""
        # Set up signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("=" * 60)
        logger.info("VECTRA-PLAYER gameHistory Capture")
        logger.info("=" * 60)

        # Start event bus
        event_bus.start()

        try:
            # Create capture service
            self.capture_service = GameHistoryCaptureService(
                event_bus=event_bus,
                output_dir=self.output_dir,
                target_rugs=self.target_rugs,
            )
            self.capture_service.start()

            logger.info(f"Capture session: {self.capture_service.session_dir}")

            # Create browser bridge
            self.bridge = BrowserBridge()
            self.bridge.on_status_change = self._on_status_change

            # Connect to browser
            logger.info("Connecting to Chrome (port 9222)...")
            logger.info("Make sure Chrome is running with: --remote-debugging-port=9222")
            self.bridge.connect()

            # Wait for connection or capture completion
            while not self._shutdown_requested:
                time.sleep(1)

                # Check if capture is complete
                if self.capture_service.is_complete:
                    logger.info("Target reached! Stopping capture...")
                    break

                # Progress update every 30 seconds
                if int(time.time()) % 30 == 0:
                    snapshot = self.capture_service.get_snapshot()
                    logger.info(
                        f"Progress: rugs={snapshot['rug_count']}/{self.target_rugs}, "
                        f"trades={snapshot['trade_count']}, "
                        f"sidebets={snapshot['sidebet_count']}, "
                        f"gamestates={snapshot['gamestate_count']}"
                    )

        except KeyboardInterrupt:
            logger.info("Capture interrupted by user")
        finally:
            self._cleanup()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_requested = True

    def _cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")

        if self.capture_service:
            self.capture_service.stop()
            logger.info(f"Capture output: {self.capture_service.session_dir}")

        if self.bridge:
            self.bridge.stop()

        event_bus.stop()

        logger.info("=" * 60)
        logger.info("CAPTURE COMPLETE")
        if self.capture_service:
            snapshot = self.capture_service.get_snapshot()
            logger.info(f"Rug pairs: {snapshot['rug_count']}/{self.target_rugs}")
            logger.info(f"Trades: {snapshot['trade_count']}")
            logger.info(f"Sidebets: {snapshot['sidebet_count']}")
            logger.info(f"Output: {snapshot['output_directory']}")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Capture gameHistory events using VECTRA-PLAYER browser connection"
    )
    parser.add_argument(
        "--min-rugs",
        type=int,
        default=4,
        help="Minimum number of rug event pairs to capture (default: 4)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: ~/rugs_data/gamehistory_captures/)",
    )

    args = parser.parse_args()

    runner = CaptureRunner(target_rugs=args.min_rugs, output_dir=args.output_dir)
    runner.run()


if __name__ == "__main__":
    main()
