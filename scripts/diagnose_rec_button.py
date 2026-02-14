#!/usr/bin/env python3
"""
Diagnostic script to test REC button behavior.

Tests the complete flow from button click to visual update.
"""

import sys
import tkinter as tk
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, "/home/devops/Desktop/VECTRA-PLAYER/src")

from services.event_bus import EventBus
from services.event_store.service import EventStoreService


def test_event_store_directly():
    """Test EventStoreService toggle directly."""
    print("\n=== Test 1: EventStoreService Direct Test ===")
    event_bus = EventBus()
    event_store = EventStoreService(event_bus)
    event_store.start()

    print(
        f"Initial state: is_recording={event_store.is_recording}, is_paused={event_store.is_paused}"
    )

    result = event_store.toggle_recording()
    print(
        f"After toggle: result={result}, is_recording={event_store.is_recording}, is_paused={event_store.is_paused}"
    )

    result2 = event_store.toggle_recording()
    print(
        f"After 2nd toggle: result={result2}, is_recording={event_store.is_recording}, is_paused={event_store.is_paused}"
    )

    event_store.stop()
    print(
        "EventStoreService test PASSED"
        if result and not result2
        else "EventStoreService test FAILED"
    )


def test_recording_controller():
    """Test RecordingController toggle."""
    print("\n=== Test 2: RecordingController Test ===")
    from ui.controllers.recording_controller import RecordingController

    event_bus = EventBus()
    event_bus.start()  # Must start EventBus for event delivery
    event_store = EventStoreService(event_bus)
    event_store.start()

    controller = RecordingController(event_store, event_bus)

    print(f"Initial state: is_recording={controller.is_recording}")

    # Subscribe to event to verify publishing
    events_received = []

    def on_toggle(data):
        events_received.append(data)
        print(f"  Event received: {data}")

    from services.event_bus import Events

    event_bus.subscribe(Events.RECORDING_TOGGLED, on_toggle, weak=False)

    result = controller.toggle()
    print(f"After toggle: result={result}, is_recording={controller.is_recording}")

    result2 = controller.toggle()
    print(f"After 2nd toggle: result={result2}, is_recording={controller.is_recording}")

    # Give EventBus time to process async events
    import time

    time.sleep(0.2)

    print(f"Events received: {len(events_received)}")

    event_store.stop()
    event_bus.stop()
    passed = result and not result2 and len(events_received) == 2
    print("RecordingController test PASSED" if passed else "RecordingController test FAILED")


def test_minimal_window_toggle():
    """Test MinimalWindow recording toggle integration."""
    print("\n=== Test 3: MinimalWindow Toggle Test ===")
    from decimal import Decimal

    from ui.minimal_window import MinimalWindow

    root = tk.Tk()
    root.withdraw()  # Hide window

    event_bus = EventBus()
    event_store = EventStoreService(event_bus)
    event_store.start()

    mock_game_state = MagicMock()
    mock_game_state.get.return_value = Decimal("1.0")
    mock_config = MagicMock()

    window = MinimalWindow(
        root=root,
        game_state=mock_game_state,
        event_bus=event_bus,
        config=mock_config,
        event_store=event_store,
    )

    # Check if recording toggle exists
    print(f"recording_toggle exists: {window.recording_toggle is not None}")
    print(f"recording_controller exists: {window.recording_controller is not None}")

    if window.recording_toggle:
        print(f"Initial toggle state: is_on={window.recording_toggle.is_recording}")

    # Simulate toggle click by directly invoking the switch's click handler
    print("\n--- Simulating toggle click ---")

    # Create a mock event and call the click handler directly
    class MockEvent:
        x = 30
        y = 12

    window.recording_toggle.switch._on_click(MockEvent())

    # Process Tk events
    root.update()

    if window.recording_toggle:
        print(f"After toggle: is_on={window.recording_toggle.is_recording}")

    result = window.recording_controller.is_recording

    print(f"recording_controller.is_recording: {window.recording_controller.is_recording}")
    print(f"_on_rec_toggled returned: {result}")

    # Check if toggle state changed
    passed = result is True and window.recording_toggle.is_recording is True
    print(f"\nMinimalWindow toggle test {'PASSED' if passed else 'FAILED'}")

    if not passed:
        print("\n!!! DIAGNOSIS: Toggle did NOT switch to recording state !!!")
        print("Possible causes:")
        print("  1. recording_controller not available")
        print("  2. toggle.set_state() not working")
        print("  3. Exception in _on_rec_toggled()")

    event_store.stop()
    root.destroy()
    return passed


def test_button_config_directly():
    """Test Tkinter button config directly."""
    print("\n=== Test 4: Direct Tkinter Button Config Test ===")

    root = tk.Tk()
    root.withdraw()

    btn = tk.Button(root, text="TEST", bg="gray")
    btn.pack()

    print(f"Initial bg: {btn.cget('bg')}")

    btn.config(bg="red", text="CHANGED")
    root.update()

    print(f"After config bg: {btn.cget('bg')}")
    print(f"After config text: {btn.cget('text')}")

    passed = btn.cget("bg") == "red" and btn.cget("text") == "CHANGED"
    print(f"Tkinter config test {'PASSED' if passed else 'FAILED'}")

    root.destroy()
    return passed


if __name__ == "__main__":
    print("=" * 60)
    print("Recording Toggle Diagnostic Tests")
    print("=" * 60)

    test_event_store_directly()
    test_recording_controller()
    test_button_config_directly()
    test_minimal_window_toggle()

    print("\n" + "=" * 60)
    print("Diagnostics complete")
    print("=" * 60)
