#!/usr/bin/env python3
"""
Visual test for recording toggle - shows actual window to verify visual changes.
"""

import sys
import tkinter as tk
from decimal import Decimal
from unittest.mock import MagicMock

sys.path.insert(0, "/home/devops/Desktop/VECTRA-PLAYER/src")

from services.event_bus import EventBus
from services.event_store.service import EventStoreService
from ui.minimal_window import MinimalWindow


def main():
    """Create and show MinimalWindow with recording toggle."""
    print("Creating MinimalWindow with recording toggle...")

    # Create components
    root = tk.Tk()
    event_bus = EventBus()
    event_bus.start()

    event_store = EventStoreService(event_bus)
    event_store.start()

    mock_game_state = MagicMock()
    mock_game_state.get.return_value = Decimal("1.0")
    mock_config = MagicMock()

    # Create window
    window = MinimalWindow(
        root=root,
        game_state=mock_game_state,
        event_bus=event_bus,
        config=mock_config,
        event_store=event_store,
    )

    # Verify components exist
    print(f"recording_toggle exists: {window.recording_toggle is not None}")
    print(f"recording_controller exists: {window.recording_controller is not None}")

    if window.recording_toggle:
        print(f"Initial toggle state: is_recording={window.recording_toggle.is_recording}")

    print("\n*** Click the toggle switch to see it change ***")
    print("*** The toggle should slide and change color when clicked ***")
    print("*** Close the window when done ***\n")

    # Run the main loop
    try:
        root.mainloop()
    finally:
        event_store.stop()
        event_bus.stop()

    print("\nTest complete!")


if __name__ == "__main__":
    main()
