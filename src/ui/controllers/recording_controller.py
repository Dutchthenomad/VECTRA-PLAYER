"""
Recording Controller - Manages EventStore recording state from UI.

Provides:
- 1-click toggle for recording on/off
- Status reporting (event count, game count)
- Event publishing for UI updates
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.event_bus import EventBus
    from services.event_store.service import EventStoreService

from services.event_bus import Events


class RecordingController:
    """
    Controller for managing recording state.

    Bridges the UI (REC button) with EventStoreService.
    """

    def __init__(
        self,
        event_store: "EventStoreService",
        event_bus: "EventBus",
    ):
        """
        Initialize recording controller.

        Args:
            event_store: EventStoreService instance to control
            event_bus: EventBus for publishing state changes
        """
        self.event_store = event_store
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

    @property
    def is_recording(self) -> bool:
        """Whether currently recording."""
        return self.event_store.is_recording

    def toggle(self) -> bool:
        """
        Toggle recording state.

        Returns:
            New recording state (True = recording, False = paused)
        """
        new_state = self.event_store.toggle_recording()

        # Publish event for UI updates
        self.event_bus.publish(
            Events.RECORDING_TOGGLED,
            {
                "is_recording": new_state,
                "event_count": self.event_store.event_count,
                "game_count": len(self.event_store.recorded_game_ids),
            },
        )

        if new_state:
            self.logger.info("Recording STARTED")
            self.event_bus.publish(Events.RECORDING_STARTED, {})
        else:
            self.logger.info(
                f"Recording STOPPED - {self.event_store.event_count} events, "
                f"{len(self.event_store.recorded_game_ids)} games"
            )
            self.event_bus.publish(
                Events.RECORDING_STOPPED,
                {
                    "event_count": self.event_store.event_count,
                    "game_count": len(self.event_store.recorded_game_ids),
                },
            )

        return new_state

    def start(self) -> None:
        """Explicitly start recording."""
        if self.event_store.is_paused:
            self.event_store.resume()
            # Publish RECORDING_TOGGLED for UI updates
            self.event_bus.publish(
                Events.RECORDING_TOGGLED,
                {
                    "is_recording": True,
                    "event_count": self.event_store.event_count,
                    "game_count": len(self.event_store.recorded_game_ids),
                },
            )
            self.event_bus.publish(Events.RECORDING_STARTED, {})
            self.logger.info("Recording STARTED")

    def stop(self) -> None:
        """Explicitly stop recording."""
        if self.event_store.is_recording:
            self.event_store.pause()
            # Publish RECORDING_TOGGLED for UI updates
            self.event_bus.publish(
                Events.RECORDING_TOGGLED,
                {
                    "is_recording": False,
                    "event_count": self.event_store.event_count,
                    "game_count": len(self.event_store.recorded_game_ids),
                },
            )
            self.event_bus.publish(
                Events.RECORDING_STOPPED,
                {
                    "event_count": self.event_store.event_count,
                    "game_count": len(self.event_store.recorded_game_ids),
                },
            )
            self.logger.info(
                f"Recording STOPPED - {self.event_store.event_count} events, "
                f"{len(self.event_store.recorded_game_ids)} games"
            )

    def get_status(self) -> dict:
        """
        Get current recording status.

        Returns:
            Dict with is_recording, event_count, game_count
        """
        return {
            "is_recording": self.event_store.is_recording,
            "event_count": self.event_store.event_count,
            "game_count": len(self.event_store.recorded_game_ids),
        }
