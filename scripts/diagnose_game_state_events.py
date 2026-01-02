#!/usr/bin/env python3
"""
Quick diagnostic to trace exactly what GameState._on_ws_raw_event receives.

This script patches GameState temporarily to log all incoming events
with full structure analysis.

Usage:
    1. Run this script
    2. In another terminal, run ./run.sh
    3. Watch this terminal for event structure logs
    4. Press Ctrl+C to stop

This will show EXACTLY what GameState is receiving so we can fix the handler.
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DIAGNOSTIC")


def analyze_event_structure(wrapped: dict, depth: int = 0) -> None:
    """Recursively analyze event structure."""
    indent = "  " * depth

    if not isinstance(wrapped, dict):
        logger.info(f"{indent}NOT A DICT: type={type(wrapped)}, value={wrapped}")
        return

    logger.info(f"{indent}KEYS: {list(wrapped.keys())}")

    for key, value in wrapped.items():
        if isinstance(value, dict):
            logger.info(f"{indent}{key}: <dict with {len(value)} keys>")
            if depth < 3:  # Limit recursion
                analyze_event_structure(value, depth + 1)
        elif isinstance(value, list):
            logger.info(f"{indent}{key}: <list with {len(value)} items>")
        else:
            # Truncate long values
            val_str = str(value)
            if len(val_str) > 100:
                val_str = val_str[:100] + "..."
            logger.info(f"{indent}{key}: {val_str}")


def diagnostic_handler(wrapped: dict) -> None:
    """Diagnostic event handler that logs everything."""
    logger.info("\n" + "=" * 70)
    logger.info("INCOMING EVENT TO GameState._on_ws_raw_event")
    logger.info("=" * 70)

    # Full structure
    analyze_event_structure(wrapped)

    # Try to extract event name using various paths
    logger.info("\n--- EXTRACTION ATTEMPTS ---")

    # Path 1: wrapped.get("data", {}).get("event")
    data = wrapped.get("data", {})
    if isinstance(data, dict):
        event_name = data.get("event")
        logger.info(f"Path wrapped['data']['event']: {event_name}")

        # Path 2: wrapped.get("data", {}).get("data", {})
        inner = data.get("data", {})
        if isinstance(inner, dict):
            logger.info(f"Path wrapped['data']['data'] keys: {list(inner.keys())}")
            logger.info(f"  tickCount: {inner.get('tickCount', 'MISSING')}")
            logger.info(f"  tick: {inner.get('tick', 'MISSING')}")
            logger.info(f"  phase: {inner.get('phase', 'MISSING')}")
            logger.info(f"  active: {inner.get('active', 'MISSING')}")
            logger.info(f"  multiplier: {inner.get('multiplier', 'MISSING')}")
            logger.info(f"  gameId: {inner.get('gameId', 'MISSING')}")
        else:
            logger.info(f"Path wrapped['data']['data']: NOT A DICT ({type(inner)})")
    else:
        logger.info(f"Path wrapped['data']: NOT A DICT ({type(data)})")

    # Path 2: Direct access (if EventBus doesn't wrap)
    event_name_direct = wrapped.get("event")
    logger.info(f"Path wrapped['event']: {event_name_direct}")

    if event_name_direct == "gameStateUpdate":
        inner_direct = wrapped.get("data", {})
        if isinstance(inner_direct, dict):
            logger.info(f"DIRECT Path wrapped['data'] keys: {list(inner_direct.keys())}")
            logger.info(f"  tickCount: {inner_direct.get('tickCount', 'MISSING')}")
            logger.info(f"  phase: {inner_direct.get('phase', 'MISSING')}")

    logger.info("=" * 70 + "\n")


def main():
    """Run diagnostic by subscribing to EventBus."""
    from services.event_bus import Events, event_bus

    logger.info("=" * 70)
    logger.info("GAMESTATE EVENT DIAGNOSTIC")
    logger.info("=" * 70)
    logger.info("Subscribing to WS_RAW_EVENT...")
    logger.info("Run ./run.sh in another terminal")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70 + "\n")

    # Subscribe with our diagnostic handler
    event_bus.subscribe(Events.WS_RAW_EVENT, diagnostic_handler, weak=False)
    event_bus.start()

    try:
        import time
        event_count = 0
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\nStopping diagnostic...")

    event_bus.stop()
    logger.info("Done.")


if __name__ == "__main__":
    main()
