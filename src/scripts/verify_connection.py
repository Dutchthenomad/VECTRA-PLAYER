#!/usr/bin/env python3
"""
Connection Verification Script

Verifies:
1. CDP WebSocket interception is receiving events from rugs.fun
2. Button clicks work through the BrowserBridge

Usage:
    # From src/ directory:
    python3 scripts/verify_connection.py

    # With button test:
    python3 scripts/verify_connection.py --test-button
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from browser.bridge import BridgeStatus, BrowserBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def print_status(label: str, value: str, ok: bool = True):
    """Print a status line with checkmark or X."""
    symbol = "✓" if ok else "✗"
    color = "\033[92m" if ok else "\033[91m"
    reset = "\033[0m"
    print(f"  {color}{symbol}{reset} {label}: {value}")


async def verify_connection(bridge: BrowserBridge, timeout: float = 30.0) -> bool:
    """
    Verify CDP connection and WebSocket interception.

    Returns True if WebSocket events are being received.
    """
    print_header("CDP Connection Verification")

    # Check bridge status
    if bridge.status != BridgeStatus.CONNECTED:
        print_status("Bridge Status", bridge.status.value, ok=False)
        return False

    print_status("Bridge Status", "CONNECTED", ok=True)

    # Get interceptor stats
    if not bridge._cdp_interceptor:
        print_status("CDP Interceptor", "Not initialized", ok=False)
        return False

    stats = bridge._cdp_interceptor.get_stats()
    print_status(
        "CDP Interceptor Connected",
        str(stats.get("is_connected", False)),
        ok=stats.get("is_connected", False),
    )
    print_status(
        "Rugs WebSocket Found",
        str(stats.get("has_rugs_websocket", False)),
        ok=stats.get("has_rugs_websocket", False),
    )

    initial_received = stats.get("events_received", 0)
    print(f"\n  Initial events received: {initial_received}")

    if initial_received > 0:
        print_status("WebSocket Events", f"{initial_received} events received", ok=True)
        return True

    # Wait for events
    print(f"\n  Waiting up to {timeout}s for WebSocket events...")
    print("  (Navigate to rugs.fun in the connected browser)")

    start = time.time()
    last_count = 0
    while time.time() - start < timeout:
        await asyncio.sleep(1.0)
        stats = bridge._cdp_interceptor.get_stats()
        current = stats.get("events_received", 0)

        if current > last_count:
            elapsed = time.time() - start
            print(f"  [{elapsed:.1f}s] Events received: {current}")
            last_count = current

        if current > 0:
            print_status("\nWebSocket Events", f"{current} events received!", ok=True)
            return True

    print_status("\nWebSocket Events", "No events received (timeout)", ok=False)
    print("\n  Troubleshooting:")
    print("  - Make sure Chrome is navigated to rugs.fun")
    print("  - Check if the page has a WebSocket connection")
    print("  - Try refreshing the rugs.fun page")
    return False


async def test_button_click(bridge: BrowserBridge, button: str = "BUY") -> bool:
    """
    Test a button click through the BrowserBridge.

    Returns True if click was queued successfully.
    """
    print_header(f"Button Click Test: {button}")

    if bridge.status != BridgeStatus.CONNECTED:
        print_status("Bridge Status", "Not connected", ok=False)
        return False

    # Get initial click stats
    initial_stats = bridge.get_click_stats()
    initial_success = initial_stats.get(button, {}).get("success", 0)

    print(f"  Queuing {button} click...")

    # Queue the click
    if button == "BUY":
        bridge.on_buy_clicked()
    elif button == "SELL":
        bridge.on_sell_clicked()
    elif button == "SIDEBET":
        bridge.on_sidebet_clicked()
    else:
        print_status("Button", f"Unknown button: {button}", ok=False)
        return False

    # Wait for click to be processed
    await asyncio.sleep(2.0)

    # Check click stats
    final_stats = bridge.get_click_stats()
    final_success = final_stats.get(button, {}).get("success", 0)
    final_failure = final_stats.get(button, {}).get("failure", 0)

    if final_success > initial_success:
        methods = final_stats.get(button, {}).get("methods", {})
        method_used = next(iter(methods.keys()), "unknown")
        print_status("Click Result", f"SUCCESS (method: {method_used})", ok=True)
        return True
    elif final_failure > 0:
        print_status("Click Result", f"FAILED ({final_failure} failures)", ok=False)
        print("\n  Troubleshooting:")
        print("  - Make sure rugs.fun trading panel is visible")
        print("  - Check if the button exists on the page")
        print("  - Try refreshing the page")
        return False
    else:
        print_status("Click Result", "No result recorded (click may still be processing)", ok=False)
        return False


async def main():
    parser = argparse.ArgumentParser(description="Verify VECTRA-PLAYER connection")
    parser.add_argument(
        "--test-button", action="store_true", help="Test a button click (default: BUY)"
    )
    parser.add_argument(
        "--button", default="BUY", choices=["BUY", "SELL", "SIDEBET"], help="Button to test"
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout in seconds")
    parser.add_argument(
        "--skip-connect", action="store_true", help="Skip connection (assume already connected)"
    )
    args = parser.parse_args()

    print_header("VECTRA-PLAYER Connection Verification")
    print("  This script verifies:")
    print("  1. CDP WebSocket interception is working")
    print("  2. Button clicks work through the browser bridge")

    # Create bridge
    bridge = BrowserBridge()

    if not args.skip_connect:
        print("\n  Starting browser bridge...")
        bridge.start_async_loop()
        bridge.connect()

        # Wait for connection
        print("  Waiting for browser connection...")
        for _ in range(30):
            await asyncio.sleep(1.0)
            if bridge.status == BridgeStatus.CONNECTED:
                break
            elif bridge.status == BridgeStatus.ERROR:
                print_status("Connection", "ERROR - check browser/CDP", ok=False)
                return 1

        if bridge.status != BridgeStatus.CONNECTED:
            print_status("Connection", "TIMEOUT - browser did not connect", ok=False)
            return 1

        print_status("Connection", "SUCCESS", ok=True)

    # Verify WebSocket
    ws_ok = await verify_connection(bridge, timeout=args.timeout)

    # Test button if requested
    btn_ok = True
    if args.test_button:
        btn_ok = await test_button_click(bridge, args.button)

    # Summary
    print_header("Summary")
    print_status("WebSocket Interception", "WORKING" if ws_ok else "NOT WORKING", ok=ws_ok)
    if args.test_button:
        print_status("Button Click", "WORKING" if btn_ok else "NOT WORKING", ok=btn_ok)

    # Keep running for a bit if everything works
    if ws_ok:
        print("\n  Monitoring events (Ctrl+C to stop)...")
        try:
            while True:
                await asyncio.sleep(5.0)
                stats = bridge._cdp_interceptor.get_stats()
                print(
                    f"  Events: {stats.get('events_received', 0)} received, {stats.get('events_sent', 0)} sent"
                )
        except KeyboardInterrupt:
            print("\n  Stopped.")

    bridge.stop()
    return 0 if ws_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
