"""
Raw capture handlers for MainWindow (Developer Tools).
"""

import logging
import subprocess
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class CaptureHandlersMixin:
    """Mixin providing raw capture handler functionality for MainWindow."""

    def _toggle_raw_capture(self: "MainWindow"):
        """Toggle raw WebSocket capture on/off."""
        try:
            if self.raw_capture_recorder.is_capturing:
                summary = self.raw_capture_recorder.stop_capture()
                if summary:
                    self.log(f"Raw capture stopped: {summary['total_events']} events")
            else:
                capture_file = self.raw_capture_recorder.start_capture()
                if capture_file:
                    self.log(f"Raw capture started: {capture_file.name}")
                else:
                    self.toast.show("Failed to start capture", "error")
        except Exception as e:
            logger.error(f"Failed to toggle raw capture: {e}")
            self.toast.show(f"Error: {e}", "error")

    def _on_raw_capture_started(self: "MainWindow", capture_file):
        """Callback when raw capture starts."""

        def update_ui():
            self.dev_menu.entryconfig(self.dev_capture_item_index, label="Stop Raw Capture")
            self.toast.show(f"Capturing to: {capture_file.name}", "success")

        self.ui_dispatcher.submit(update_ui)

    def _on_raw_capture_stopped(self: "MainWindow", capture_file, event_counts):
        """Callback when raw capture stops."""

        def update_ui():
            self.dev_menu.entryconfig(self.dev_capture_item_index, label="Start Raw Capture")
            total = sum(event_counts.values())
            self.toast.show(f"Capture complete: {total} events", "info")

        self.ui_dispatcher.submit(update_ui)

    def _on_raw_event_captured(self: "MainWindow", event_name, seq_num):
        """Callback for each captured event (throttled logging)."""
        if seq_num % 100 == 0:
            logger.debug(f"Raw capture: {seq_num} events captured (last: {event_name})")

    def _analyze_last_capture(self: "MainWindow"):
        """Analyze the most recent capture file."""
        try:
            capture_file = self.raw_capture_recorder.get_last_capture_file()
            if not capture_file:
                self.toast.show("No captures found", "info")
                return

            script_path = Path(__file__).parent.parent.parent / "scripts" / "analyze_raw_capture.py"
            if not script_path.exists():
                self.toast.show("Analysis script not found", "error")
                return

            result = subprocess.run(
                ["python3", str(script_path), str(capture_file), "--report"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.toast.show("Analysis complete - check captures folder", "success")
                self.log(result.stdout)
            else:
                self.toast.show(f"Analysis failed: {result.stderr}", "error")

        except subprocess.TimeoutExpired:
            self.toast.show("Analysis timed out", "error")
        except Exception as e:
            logger.error(f"Failed to analyze capture: {e}")
            self.toast.show(f"Error: {e}", "error")

    def _open_captures_folder(self: "MainWindow"):
        """Open the raw captures folder in file manager."""
        try:
            captures_dir = self.raw_capture_recorder.capture_dir
            captures_dir.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(["xdg-open", str(captures_dir)])
            self.toast.show(f"Opened: {captures_dir}", "info")
        except Exception as e:
            logger.error(f"Failed to open captures folder: {e}")
            self.toast.show(f"Error: {e}", "error")

    def _show_capture_status(self: "MainWindow"):
        """Show current raw capture status in a dialog."""
        try:
            status = self.raw_capture_recorder.get_status()

            event_counts_str = "None"
            if status["event_counts"]:
                lines = [
                    f"  {k}: {v}"
                    for k, v in sorted(status["event_counts"].items(), key=lambda x: -x[1])
                ]
                event_counts_str = "\n".join(lines[:10])
                if len(status["event_counts"]) > 10:
                    event_counts_str += f"\n  ... and {len(status['event_counts']) - 10} more"

            status_text = f"""Raw Capture Status

Capturing: {"Yes" if status["is_capturing"] else "No"}
Connected: {"Yes" if status["connected"] else "No"}
Total Events: {status["total_events"]}

Current File: {status["capture_file"] or "None"}

Event Counts (Top 10):
{event_counts_str}

Captures Directory: {self.raw_capture_recorder.capture_dir}
"""
            messagebox.showinfo("Raw Capture Status", status_text)
        except Exception as e:
            logger.error(f"Failed to get capture status: {e}")
            messagebox.showerror("Error", f"Failed to get status: {e}")

    def _open_debug_terminal(self: "MainWindow"):
        """Open WebSocket debug terminal window."""
        from services.event_bus import Events, event_bus
        from ui.debug_terminal import DebugTerminal

        if not hasattr(self, "_debug_terminal") or self._debug_terminal is None:

            def on_close():
                try:
                    if (
                        hasattr(self, "_debug_terminal_event_handler")
                        and self._debug_terminal_event_handler
                    ):
                        event_bus.unsubscribe(
                            Events.WS_RAW_EVENT, self._debug_terminal_event_handler
                        )
                finally:
                    self._debug_terminal_event_handler = None
                    self._debug_terminal = None

            self._debug_terminal = DebugTerminal(self.root, on_close=on_close)

            def handle_ws_raw_event(e):
                payload = e.get("data", {}) if isinstance(e, dict) else {}
                self.ui_dispatcher.submit(
                    lambda: self._debug_terminal.log_event(payload)
                    if self._debug_terminal
                    else None
                )

            self._debug_terminal_event_handler = handle_ws_raw_event
            event_bus.subscribe(Events.WS_RAW_EVENT, self._debug_terminal_event_handler)
        else:
            self._debug_terminal.show()
