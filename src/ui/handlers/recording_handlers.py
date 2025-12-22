"""
Recording handlers for MainWindow (Demo + Unified Recording).
"""

import logging
import time
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class RecordingHandlersMixin:
    """Mixin providing recording handler functionality for MainWindow."""

    # ========================================================================
    # DEMO RECORDING HANDLERS (Phase 10)
    # ========================================================================

    def _start_demo_session(self: "MainWindow"):
        """Start a new demo recording session."""
        try:
            session_id = self.demo_recorder.start_session()
            self.log(f"Demo session started: {session_id}")
            self.toast.show("Demo session started", "success")
            logger.info(f"Demo recording session started: {session_id}")
        except Exception as e:
            logger.error(f"Failed to start demo session: {e}")
            self.toast.show(f"Failed to start session: {e}", "error")

    def _end_demo_session(self: "MainWindow"):
        """End the current demo recording session."""
        try:
            self.demo_recorder.end_session()
            self.log("Demo session ended")
            self.toast.show("Demo session ended", "info")
            logger.info("Demo recording session ended")
        except Exception as e:
            logger.error(f"Failed to end demo session: {e}")
            self.toast.show(f"Failed to end session: {e}", "error")

    def _start_demo_game(self: "MainWindow"):
        """Start recording a new game in the demo session."""
        game_id = self.state.get("game_id")
        if not game_id:
            game_id = f"game_{int(time.time())}"

        try:
            self.demo_recorder.start_game(game_id)
            self.log(f"Demo game started: {game_id}")
            self.toast.show(f"Recording game: {game_id[:20]}...", "success")
            logger.info(f"Demo recording game started: {game_id}")
        except Exception as e:
            logger.error(f"Failed to start demo game: {e}")
            self.toast.show(f"Failed to start game: {e}", "error")

    def _end_demo_game(self: "MainWindow"):
        """End recording the current game."""
        try:
            self.demo_recorder.end_game()
            self.log("Demo game ended")
            self.toast.show("Game recording saved", "info")
            logger.info("Demo recording game ended")
        except Exception as e:
            logger.error(f"Failed to end demo game: {e}")
            self.toast.show(f"Failed to end game: {e}", "error")

    def _show_demo_status(self: "MainWindow"):
        """Show current demo recording status in a dialog."""
        try:
            status = self.demo_recorder.get_status()
            status_text = f"""Demo Recording Status

Session Active: {"Yes" if status["session_active"] else "No"}
Session ID: {status.get("session_id", "N/A")}
Session Start: {status.get("session_start", "N/A")}

Game Active: {"Yes" if status["game_active"] else "No"}
Game ID: {status.get("game_id", "N/A")}
Actions Recorded: {status.get("action_count", 0)}

Output Directory: {self.demo_recorder.base_dir}
"""
            messagebox.showinfo("Demo Recording Status", status_text)
        except Exception as e:
            logger.error(f"Failed to get demo status: {e}")
            messagebox.showerror("Error", f"Failed to get status: {e}")

    # ========================================================================
    # UNIFIED RECORDING HANDLERS (Phase 10.5)
    # ========================================================================

    def _show_recording_config(self: "MainWindow"):
        """Show the recording configuration dialog."""
        try:
            if hasattr(self, "recording_controller"):
                self.recording_controller.show_config_dialog()
            else:
                logger.error("RecordingController not initialized")
                self.toast.show("Recording controller not available", "error")
        except Exception as e:
            logger.error(f"Failed to show recording config: {e}")
            self.toast.show(f"Error: {e}", "error")

    def _stop_recording_session(self: "MainWindow"):
        """Stop the current recording session."""
        try:
            if hasattr(self, "recording_controller"):
                if self.recording_controller.is_active:
                    self.recording_controller.stop_session()
                else:
                    self.toast.show("No active recording session", "info")
            else:
                logger.error("RecordingController not initialized")
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            self.toast.show(f"Error: {e}", "error")

    def _show_recording_status(self: "MainWindow"):
        """Show current recording status in a dialog."""
        try:
            if hasattr(self, "recording_controller"):
                status = self.recording_controller.get_status()
                status_text = f"""Recording Status

State: {status.get("state", "unknown").upper()}
Games Recorded: {status.get("games_recorded", 0)}
Capture Mode: {status.get("capture_mode", "unknown")}
Game Limit: {status.get("game_limit", "infinite") or "infinite"}
Data Feed Healthy: {"Yes" if status.get("is_healthy", True) else "No (Monitor Mode)"}
Current Game: {status.get("current_game_id", "None") or "None"}

Recordings Directory: {self.recording_controller.recordings_path}
"""
                messagebox.showinfo("Recording Status", status_text)
            else:
                messagebox.showinfo("Recording Status", "Recording controller not initialized")
        except Exception as e:
            logger.error(f"Failed to get recording status: {e}")
            messagebox.showerror("Error", f"Failed to get status: {e}")

    def _toggle_recording_from_button(self: "MainWindow"):
        """Toggle recording on/off from the status bar button."""
        try:
            if not hasattr(self, "recording_controller"):
                logger.warning("RecordingController not initialized yet")
                return

            if self.recording_controller.is_active:
                self.recording_controller.stop_session()
                self._update_recording_toggle_ui(False)
                self.toast.show("Recording stopped", "info")
            else:
                if self.recording_controller.start_session():
                    self._update_recording_toggle_ui(True)
                    self.toast.show("Recording started", "success")
        except Exception as e:
            logger.error(f"Failed to toggle recording: {e}")
            self.toast.show(f"Recording error: {e}", "error")

    def _update_recording_toggle_ui(self: "MainWindow", is_recording: bool):
        """Update the recording toggle button appearance."""
        if not hasattr(self, "recording_toggle"):
            return

        if is_recording:
            self.recording_toggle.config(
                text="\u23fa REC ON",
                bg="#cc0000",
                fg="white",
            )
        else:
            self.recording_toggle.config(
                text="\u23fa REC OFF",
                bg="#333333",
                fg="#888888",
            )
