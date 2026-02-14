#!/usr/bin/env python3
"""
Alpha Test: Bot Execution with Live Mirroring

This script connects to the Flask dashboard's live feed and mirrors
paper trading decisions to real browser clicks when EXECUTE is enabled.

Architecture:
- Flask Dashboard (port 5005): Paper trading, visualization, WebSocket to rugs.fun
- This Script: Mirrors Flask decisions to browser buttons via CDP

Flow:
1. Start Flask dashboard with live mode
2. This script connects to Flask's SocketIO
3. Flask makes paper trading decisions → emits live_tick
4. This script receives decisions → clicks browser buttons if EXECUTE ON

Usage:
1. Start Flask: cd src && python -m recording_ui.app --port 5005
2. Start Chrome: google-chrome --remote-debugging-port=9222 --user-data-dir=~/.gamebot/chrome_profiles/rugs_bot
3. Run this: python scripts/alpha_test_bot_execution.py
4. In Flask dashboard: Select strategy → Start Live
5. In this window: CONNECT → SYNC → EXECUTE (when ready)
"""

import logging
import sys
import tkinter as tk
from decimal import Decimal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.bet_amount_sequencer import calculate_optimal_sequence
from bot.execution_bridge import BotExecutionBridge
from bot.live_execution_client import LiveExecutionClient
from bot.simple_trading_adapter import SimpleTradingAdapter
from browser.bridge import BrowserBridge
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# UI Colors
BG_COLOR = "#1a1a2e"
TEXT_COLOR = "#ffffff"
TEXT_DIM = "#888888"
ACCENT_COLOR = "#4a90d9"
DANGER_COLOR = "#cc3333"
SUCCESS_COLOR = "#00cc55"


class AlphaTestWindow:
    """
    Compact control window for bot execution testing.

    Provides:
    - CONNECT: Attach to Chrome via CDP
    - SYNC: Connect to Flask SocketIO for live feed
    - EXECUTE: Toggle real bet execution
    - Live tick display from Flask
    - Bet placement log
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ALPHA TEST - Execution Control")
        self.root.configure(bg=BG_COLOR)

        # Components
        self.config = Config()
        self.browser_bridge = BrowserBridge()

        # Simple trading adapter (wraps BrowserBridge)
        self.trading_adapter = SimpleTradingAdapter(
            browser_bridge=self.browser_bridge,
        )

        # Execution bridge
        self.execution_bridge = BotExecutionBridge(
            trading_controller=self.trading_adapter,
            browser_bridge=self.browser_bridge,
        )

        # Live execution client (connects to Flask)
        self.live_client = LiveExecutionClient(
            flask_url="http://localhost:5005",
            execution_bridge=self.execution_bridge,
        )

        # Set callbacks for UI updates
        self.live_client.set_tick_callback(self._on_tick)
        self.live_client.set_bet_callback(self._on_bet_detected)

        # UI state
        self._browser_connected = False
        self._flask_synced = False
        self._session_id: str | None = None

        # Build UI
        self._create_ui()

        # Position window
        self.root.attributes("-topmost", True)
        self.root.geometry("500x350+50+50")

    def _create_ui(self):
        """Create the control panel UI."""
        # Main container
        main = tk.Frame(self.root, bg=BG_COLOR, padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            main,
            text="BOT EXECUTION CONTROL",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("Arial", 14, "bold"),
        ).pack(pady=(0, 15))

        # Connection buttons row
        conn_frame = tk.Frame(main, bg=BG_COLOR)
        conn_frame.pack(fill=tk.X, pady=5)

        # CONNECT button (Chrome CDP)
        self.connect_btn = tk.Button(
            conn_frame,
            text="CONNECT",
            bg=ACCENT_COLOR,
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            command=self._on_connect,
        )
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        # SYNC button (Flask SocketIO)
        self.sync_btn = tk.Button(
            conn_frame,
            text="SYNC",
            bg=ACCENT_COLOR,
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            command=self._on_sync,
        )
        self.sync_btn.pack(side=tk.LEFT, padx=5)

        # EXECUTE toggle
        self.execute_btn = tk.Button(
            conn_frame,
            text="EXECUTE: OFF",
            bg=DANGER_COLOR,
            fg="white",
            font=("Arial", 10, "bold"),
            width=14,
            command=self._on_execute_toggle,
        )
        self.execute_btn.pack(side=tk.LEFT, padx=5)

        # Status row
        status_frame = tk.Frame(main, bg=BG_COLOR)
        status_frame.pack(fill=tk.X, pady=10)

        tk.Label(status_frame, text="Chrome:", bg=BG_COLOR, fg=TEXT_DIM).pack(side=tk.LEFT)
        self.chrome_status = tk.Label(status_frame, text="●", bg=BG_COLOR, fg=DANGER_COLOR)
        self.chrome_status.pack(side=tk.LEFT, padx=(2, 15))

        tk.Label(status_frame, text="Flask:", bg=BG_COLOR, fg=TEXT_DIM).pack(side=tk.LEFT)
        self.flask_status = tk.Label(status_frame, text="●", bg=BG_COLOR, fg=DANGER_COLOR)
        self.flask_status.pack(side=tk.LEFT, padx=(2, 15))

        tk.Label(status_frame, text="Execute:", bg=BG_COLOR, fg=TEXT_DIM).pack(side=tk.LEFT)
        self.execute_status = tk.Label(status_frame, text="●", bg=BG_COLOR, fg=DANGER_COLOR)
        self.execute_status.pack(side=tk.LEFT, padx=2)

        # Live tick display
        tick_frame = tk.Frame(main, bg=BG_COLOR)
        tick_frame.pack(fill=tk.X, pady=10)

        tk.Label(tick_frame, text="TICK:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 12)).pack(
            side=tk.LEFT
        )
        self.tick_label = tk.Label(
            tick_frame, text="---", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Arial", 16, "bold")
        )
        self.tick_label.pack(side=tk.LEFT, padx=10)

        tk.Label(tick_frame, text="PRICE:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 12)).pack(
            side=tk.LEFT
        )
        self.price_label = tk.Label(
            tick_frame, text="---", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 16, "bold")
        )
        self.price_label.pack(side=tk.LEFT, padx=10)

        # Session ID entry
        session_frame = tk.Frame(main, bg=BG_COLOR)
        session_frame.pack(fill=tk.X, pady=5)

        tk.Label(session_frame, text="Session ID:", bg=BG_COLOR, fg=TEXT_DIM).pack(side=tk.LEFT)
        self.session_entry = tk.Entry(session_frame, width=30)
        self.session_entry.pack(side=tk.LEFT, padx=5)
        self.session_entry.insert(0, "alpha-test-001")

        # Log area
        tk.Label(main, text="Execution Log:", bg=BG_COLOR, fg=TEXT_DIM, anchor="w").pack(
            fill=tk.X, pady=(10, 2)
        )

        log_frame = tk.Frame(main, bg="#222233")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame,
            height=8,
            bg="#222233",
            fg=TEXT_COLOR,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Instructions
        tk.Label(
            main,
            text="1. CONNECT to Chrome | 2. Start Live in Flask | 3. SYNC | 4. EXECUTE when ready",
            bg=BG_COLOR,
            fg=TEXT_DIM,
            font=("Arial", 8),
        ).pack(pady=(10, 0))

    def _log(self, msg: str):
        """Add message to log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _on_connect(self):
        """Connect to Chrome via CDP."""
        self._log("Connecting to Chrome...")
        try:
            # Start connection (async, non-blocking)
            self.browser_bridge.connect()

            # Wait a moment for connection to establish
            self.root.after(2000, self._check_connection)
            self._log("Connecting... please wait")
        except Exception as e:
            self._log(f"✗ Chrome error: {e}")

    def _check_connection(self):
        """Check if browser connection was successful."""
        import requests

        # Check CDP directly - more reliable than bridge status
        try:
            resp = requests.get("http://localhost:9222/json/version", timeout=2)
            if resp.status_code == 200:
                self._browser_connected = True
                self.chrome_status.config(fg=SUCCESS_COLOR)
                self.connect_btn.config(text="CONNECTED", bg=SUCCESS_COLOR)
                self._log("✓ Chrome connected via CDP")
                return
        except Exception:
            pass

        # Retry logic
        if not hasattr(self, "_connect_attempts"):
            self._connect_attempts = 0
        self._connect_attempts += 1

        if self._connect_attempts < 5:
            self._log(f"Still connecting... (attempt {self._connect_attempts})")
            self.root.after(1000, self._check_connection)
        else:
            self._log("✗ Failed to connect to Chrome - is it running on port 9222?")
            self._connect_attempts = 0

    def _on_sync(self):
        """Connect to Flask SocketIO and join session."""
        import requests

        self._log("Discovering active Flask sessions...")

        try:
            # First, discover active sessions from Flask
            resp = requests.get("http://localhost:5005/api/live/sessions", timeout=3)
            if resp.status_code != 200:
                self._log("✗ Failed to query Flask for active sessions")
                return

            data = resp.json()
            sessions = data.get("sessions", [])

            if not sessions:
                self._log("✗ No active live sessions in Flask")
                self._log("  → Start Live mode in the backtest viewer first!")
                return

            # Use the first active session
            session_info = sessions[0]
            session_id = session_info["session_id"]
            strategy_name = session_info.get("strategy_name", "unknown")

            # Update the entry field to show discovered session
            self.session_entry.delete(0, "end")
            self.session_entry.insert(0, session_id[:20] + "...")  # Truncate UUID

            self._log(f"Found session: {strategy_name} ({session_id[:8]}...)")

            # Connect to Flask SocketIO
            if not self.live_client.is_connected:
                if not self.live_client.connect():
                    self._log("✗ Failed to connect to Flask SocketIO")
                    return

            # Join the session - use a minimal strategy (Flask has the real one)
            self.live_client.join_session(session_id, {"name": "mirror-client"})
            self._session_id = session_id

            self._flask_synced = True
            self.flask_status.config(fg=SUCCESS_COLOR)
            self.sync_btn.config(text="SYNCED", bg=SUCCESS_COLOR)
            self._log(f"✓ Synced with Flask session: {session_id[:8]}...")
            self._log("  Now receiving live ticks from Flask")

        except Exception as e:
            self._log(f"✗ Sync error: {e}")

    def _on_execute_toggle(self):
        """Toggle real execution mode."""
        if not self._browser_connected:
            self._log("✗ Connect to Chrome first!")
            return

        if not self._flask_synced:
            self._log("✗ Sync with Flask first!")
            return

        if self.live_client.is_enabled:
            # Disable
            self.live_client.disable_execution()
            self.execute_btn.config(text="EXECUTE: OFF", bg=DANGER_COLOR)
            self.execute_status.config(fg=DANGER_COLOR)
            self._log("⬇ Execution DISABLED")
        else:
            # Enable
            self.live_client.enable_execution()
            self.execute_btn.config(text="EXECUTE: ON", bg=SUCCESS_COLOR)
            self.execute_status.config(fg=SUCCESS_COLOR)
            self._log("⚠ EXECUTION ENABLED - Real bets will be placed!")

    def _on_tick(self, tick_count: int, price: float):
        """Callback when tick received from Flask."""
        # Update UI (must be done in main thread)
        self.root.after(0, lambda: self._update_tick_display(tick_count, price))

    def _update_tick_display(self, tick_count: int, price: float):
        """Update tick display in UI."""
        self.tick_label.config(text=str(tick_count))
        self.price_label.config(text=f"{price:.2f}x")

    def _on_bet_detected(self, bet_num: int, size: float, tick: int):
        """Callback when bet detected from Flask."""
        msg = f"BET {bet_num}: {size:.4f} SOL @ tick {tick}"
        if self.live_client.is_enabled:
            msg += " → EXECUTING"
        else:
            msg += " (paper only)"
        self.root.after(0, lambda: self._log(msg))

    def cleanup(self):
        """Cleanup on exit."""
        if self.live_client.is_connected:
            self.live_client.disconnect()


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("ALPHA TEST: Bot Execution with Live Mirroring")
    print("=" * 60)
    print("""
This script mirrors Flask paper trading to real browser clicks.

SETUP:
1. Flask dashboard should be running on localhost:5005
2. Chrome should be running with --remote-debugging-port=9222
3. Open rugs.fun in Chrome

USAGE:
1. CONNECT - Attach to Chrome via CDP
2. In Flask: Select strategy → Click "Start Live"
3. SYNC - Connect to Flask's live feed (use same session ID)
4. EXECUTE - Toggle to enable real bet placement

The backtest viewer shows paper trading.
When EXECUTE is ON, those decisions also click browser buttons.
""")
    print("=" * 60 + "\n")

    # Verify BetAmountSequencer works
    print("Verifying BetAmountSequencer...")
    test_cases = [
        (Decimal("0"), Decimal("0.004")),
        (Decimal("0.004"), Decimal("0.002")),
        (Decimal("0.002"), Decimal("0.004")),
    ]
    for current, target in test_cases:
        seq = calculate_optimal_sequence(current, target)
        print(f"  {current} → {target}: {seq}")
    print()

    # Create window
    root = tk.Tk()
    app = AlphaTestWindow(root)

    def on_close():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
