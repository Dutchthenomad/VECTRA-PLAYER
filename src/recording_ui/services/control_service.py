"""
Control Service - Recording state management via control file.

Uses JSON files for IPC between dashboard and EventStoreService:
- Control file: Dashboard writes commands → EventStoreService reads
- Status file: EventStoreService writes state → Dashboard reads

This allows the Flask dashboard to control recording without direct coupling.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# IPC file paths (must match EventStoreService)
CONTROL_FILE = Path.home() / "rugs_data" / ".recording_control.json"
STATUS_FILE = Path.home() / "rugs_data" / ".recording_status.json"


class ControlService:
    """Service for managing recording state via control file."""

    def __init__(self, control_file: Path | None = None, status_file: Path | None = None):
        """Initialize control service.

        Args:
            control_file: Path to control file. Defaults to ~/rugs_data/.recording_control.json
            status_file: Path to status file. Defaults to ~/rugs_data/.recording_status.json
        """
        self.control_file = control_file or CONTROL_FILE
        self.status_file = status_file or STATUS_FILE
        self._start_time: float | None = None

    def _read_state(self) -> dict[str, Any]:
        """Read current state from control file."""
        try:
            if self.control_file.exists():
                with open(self.control_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not read control file: {e}")
        return {"recording": False, "updated_at": None, "started_at": None}

    def _write_state(self, state: dict[str, Any]) -> bool:
        """Write state to control file."""
        try:
            # Ensure parent directory exists
            self.control_file.parent.mkdir(parents=True, exist_ok=True)

            state["updated_at"] = datetime.now().isoformat()
            state["timestamp"] = time.time()  # EventStoreService checks this for freshness
            with open(self.control_file, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Could not write control file: {e}")
            return False

    def _read_status(self) -> dict[str, Any]:
        """Read actual status from EventStoreService's status file."""
        try:
            if self.status_file.exists():
                with open(self.status_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not read status file: {e}")
        return {"is_recording": False, "event_count": 0, "game_count": 0}

    def is_recording(self) -> bool:
        """Check if recording is currently active (from EventStoreService status)."""
        status = self._read_status()
        return status.get("is_recording", False)

    def get_status(self) -> dict[str, Any]:
        """Get full recording status from EventStoreService.

        Returns:
            Dictionary with is_recording, event_count, game_count, session_id, etc.
        """
        # Get actual status from EventStoreService
        status = self._read_status()
        control = self._read_state()

        is_recording = status.get("is_recording", False)

        uptime_seconds = 0
        if is_recording and control.get("started_at"):
            try:
                started_at = datetime.fromisoformat(control["started_at"])
                uptime_seconds = (datetime.now() - started_at).total_seconds()
            except Exception:
                pass

        return {
            "is_recording": is_recording,
            "event_count": status.get("event_count", 0),
            "game_count": status.get("game_count", 0),
            "session_id": status.get("session_id"),
            "uptime_seconds": int(uptime_seconds),
            "started_at": control.get("started_at"),
            "updated_at": status.get("updated_at"),
        }

    def start_recording(self) -> bool:
        """Start recording.

        Returns:
            True if recording started, False on error
        """
        # Check actual status from EventStoreService, not control file
        if self.is_recording():
            return True  # Already recording

        state = {"recording": True, "started_at": datetime.now().isoformat()}
        return self._write_state(state)

    def stop_recording(self) -> bool:
        """Stop recording.

        Returns:
            True if recording stopped, False on error
        """
        # Check actual status from EventStoreService, not control file
        if not self.is_recording():
            return True  # Already stopped

        state = {"recording": False, "started_at": None}
        return self._write_state(state)

    def toggle_recording(self) -> bool:
        """Toggle recording state.

        Returns:
            New recording state (True if now recording)
        """
        if self.is_recording():
            self.stop_recording()
            return False
        else:
            self.start_recording()
            return True
