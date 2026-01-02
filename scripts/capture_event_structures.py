#!/usr/bin/env python3
"""
Event Structure Diagnostic Script

Captures real event structures as they flow through the system to identify
mismatches between what producers send and what consumers expect.

Usage:
    python scripts/capture_event_structures.py

This script:
1. Subscribes to WS_RAW_EVENT on EventBus
2. Captures events with full structure
3. Logs exactly what fields exist at each wrapper level
4. Outputs to docs/event_samples/ for analysis

Run this during a live session to capture real data.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.event_bus import Events, event_bus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "event_samples"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class EventCapture:
    """Captures and analyzes event structures."""

    def __init__(self):
        self.events_by_type: dict[str, list[dict]] = {}
        self.capture_count = 0
        self.max_per_type = 5  # Capture up to 5 samples per event type

    def capture(self, wrapped_event: dict) -> None:
        """Capture an event and analyze its structure."""
        self.capture_count += 1

        # Log the raw wrapper structure
        logger.info(f"\n{'='*60}")
        logger.info(f"EVENT #{self.capture_count}")
        logger.info(f"{'='*60}")

        # Level 0: What EventBus delivers
        logger.info("LEVEL 0 (EventBus wrapper):")
        logger.info(f"  Keys: {list(wrapped_event.keys())}")
        logger.info(f"  Type of 'data': {type(wrapped_event.get('data'))}")

        # Level 1: Inside 'data' wrapper
        data = wrapped_event.get("data", {})
        if isinstance(data, dict):
            logger.info("LEVEL 1 (data wrapper):")
            logger.info(f"  Keys: {list(data.keys())}")

            event_name = data.get("event", "UNKNOWN")
            logger.info(f"  event_name: {event_name}")

            # Level 2: Inside event's 'data' field
            inner_data = data.get("data", {})
            if isinstance(inner_data, dict):
                logger.info("LEVEL 2 (event data):")
                logger.info(f"  Keys: {list(inner_data.keys())}")

                # For gameStateUpdate, log critical fields
                if event_name == "gameStateUpdate":
                    logger.info("  CRITICAL FIELDS:")
                    logger.info(f"    tickCount: {inner_data.get('tickCount', 'MISSING')}")
                    logger.info(f"    tick: {inner_data.get('tick', 'MISSING')}")
                    logger.info(f"    phase: {inner_data.get('phase', 'MISSING')}")
                    logger.info(f"    active: {inner_data.get('active', 'MISSING')}")
                    logger.info(f"    multiplier: {inner_data.get('multiplier', 'MISSING')}")
                    logger.info(f"    price: {inner_data.get('price', 'MISSING')}")
                    logger.info(f"    gameId: {inner_data.get('gameId', 'MISSING')}")
                    logger.info(f"    rugged: {inner_data.get('rugged', 'MISSING')}")

            # Store sample
            if event_name not in self.events_by_type:
                self.events_by_type[event_name] = []

            if len(self.events_by_type[event_name]) < self.max_per_type:
                self.events_by_type[event_name].append({
                    "capture_num": self.capture_count,
                    "timestamp": datetime.now().isoformat(),
                    "full_structure": wrapped_event,
                    "wrapper_keys": list(wrapped_event.keys()),
                    "data_keys": list(data.keys()) if isinstance(data, dict) else str(type(data)),
                    "inner_data_keys": list(inner_data.keys()) if isinstance(inner_data, dict) else str(type(inner_data)),
                })
                logger.info(f"  [Saved sample {len(self.events_by_type[event_name])}/{self.max_per_type}]")

    def save_results(self) -> None:
        """Save captured events to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save each event type to separate file
        for event_type, samples in self.events_by_type.items():
            safe_name = event_type.replace(":", "_").replace("/", "_")
            filepath = OUTPUT_DIR / f"{timestamp}_{safe_name}.json"

            with open(filepath, "w") as f:
                json.dump({
                    "event_type": event_type,
                    "sample_count": len(samples),
                    "samples": samples,
                }, f, indent=2, default=str)

            logger.info(f"Saved {len(samples)} samples of '{event_type}' to {filepath}")

        # Save summary
        summary_path = OUTPUT_DIR / f"{timestamp}_SUMMARY.json"
        summary = {
            "capture_timestamp": timestamp,
            "total_events": self.capture_count,
            "event_types": {k: len(v) for k, v in self.events_by_type.items()},
            "critical_analysis": self._analyze_game_state_update(),
        }

        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"\nSUMMARY saved to {summary_path}")

    def _analyze_game_state_update(self) -> dict:
        """Analyze gameStateUpdate structure."""
        samples = self.events_by_type.get("gameStateUpdate", [])
        if not samples:
            return {"status": "NO_SAMPLES", "message": "No gameStateUpdate events captured"}

        sample = samples[0]
        full = sample.get("full_structure", {})
        data = full.get("data", {})
        inner = data.get("data", {}) if isinstance(data, dict) else {}

        return {
            "status": "ANALYZED",
            "wrapper_levels": {
                "level_0": list(full.keys()),
                "level_1": list(data.keys()) if isinstance(data, dict) else str(type(data)),
                "level_2": list(inner.keys()) if isinstance(inner, dict) else str(type(inner)),
            },
            "critical_fields": {
                "tickCount_location": self._find_field(full, "tickCount"),
                "phase_location": self._find_field(full, "phase"),
                "active_location": self._find_field(full, "active"),
                "multiplier_location": self._find_field(full, "multiplier"),
            },
            "recommendation": self._get_recommendation(inner),
        }

    def _find_field(self, obj: dict, field: str, path: str = "") -> str:
        """Find where a field exists in nested structure."""
        if not isinstance(obj, dict):
            return "NOT_FOUND"

        if field in obj:
            return f"{path}.{field}" if path else field

        for key, value in obj.items():
            if isinstance(value, dict):
                result = self._find_field(value, field, f"{path}.{key}" if path else key)
                if result != "NOT_FOUND":
                    return result

        return "NOT_FOUND"

    def _get_recommendation(self, inner_data: dict) -> str:
        """Get recommendation based on analysis."""
        if not isinstance(inner_data, dict):
            return "CRITICAL: inner data is not a dict!"

        has_phase = "phase" in inner_data
        has_active = "active" in inner_data
        has_tick_count = "tickCount" in inner_data

        if has_phase and has_tick_count:
            if has_active:
                return "Fields present. Check if handler is receiving correctly."
            else:
                return "No 'active' field - must derive from 'phase'."
        else:
            return f"Missing critical fields: phase={has_phase}, tickCount={has_tick_count}"


def main():
    """Run event capture diagnostic."""
    logger.info("=" * 60)
    logger.info("EVENT STRUCTURE DIAGNOSTIC")
    logger.info("=" * 60)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("Press Ctrl+C to stop and save results")
    logger.info("=" * 60)

    capture = EventCapture()

    # Subscribe to events
    event_bus.subscribe(Events.WS_RAW_EVENT, capture.capture, weak=False)
    event_bus.start()

    logger.info("Subscribed to WS_RAW_EVENT. Waiting for events...")
    logger.info("(Start the main app in another terminal to generate events)")

    try:
        # Keep running until interrupted
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nInterrupted. Saving results...")

    capture.save_results()
    event_bus.stop()

    logger.info("\n" + "=" * 60)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info(f"Captured {capture.capture_count} events")
    logger.info(f"Event types: {list(capture.events_by_type.keys())}")
    logger.info(f"Results saved to: {OUTPUT_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
