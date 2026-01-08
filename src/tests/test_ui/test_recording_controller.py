"""Tests for RecordingController."""

from unittest.mock import MagicMock

import pytest

from ui.controllers.recording_controller import RecordingController


class TestRecordingController:
    """Test RecordingController functionality."""

    @pytest.fixture
    def mock_event_store(self):
        """Create mock EventStoreService."""
        store = MagicMock()
        store.is_recording = False
        store.is_paused = True
        store.event_count = 0
        store.recorded_game_ids = set()
        return store

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock EventBus."""
        return MagicMock()

    @pytest.fixture
    def controller(self, mock_event_store, mock_event_bus):
        """Create RecordingController with mocks."""
        return RecordingController(event_store=mock_event_store, event_bus=mock_event_bus)

    def test_initial_state_not_recording(self, controller):
        """Controller should start in non-recording state."""
        assert controller.is_recording is False

    def test_toggle_starts_recording(self, controller, mock_event_store):
        """toggle() should start recording when paused."""
        mock_event_store.toggle_recording.return_value = True
        mock_event_store.is_recording = True

        result = controller.toggle()

        assert result is True
        mock_event_store.toggle_recording.assert_called_once()

    def test_toggle_stops_recording(self, controller, mock_event_store):
        """toggle() should stop recording when active."""
        mock_event_store.is_recording = True
        mock_event_store.toggle_recording.return_value = False

        result = controller.toggle()

        assert result is False
        mock_event_store.toggle_recording.assert_called_once()

    def test_toggle_publishes_event(self, controller, mock_event_store, mock_event_bus):
        """toggle() should publish RECORDING_TOGGLED event."""
        mock_event_store.toggle_recording.return_value = True

        controller.toggle()

        mock_event_bus.publish.assert_called()

    def test_get_status_returns_dict(self, controller, mock_event_store):
        """get_status() should return recording status dict."""
        mock_event_store.is_recording = True
        mock_event_store.event_count = 42
        mock_event_store.recorded_game_ids = {"game1", "game2"}

        status = controller.get_status()

        assert status["is_recording"] is True
        assert status["event_count"] == 42
        assert status["game_count"] == 2

    def test_start_recording(self, controller, mock_event_store):
        """start() should explicitly start recording."""
        mock_event_store.is_paused = True

        controller.start()

        mock_event_store.resume.assert_called_once()

    def test_stop_recording(self, controller, mock_event_store):
        """stop() should explicitly stop recording."""
        mock_event_store.is_recording = True

        controller.stop()

        mock_event_store.pause.assert_called_once()

    def test_start_publishes_events(self, controller, mock_event_store, mock_event_bus):
        """start() should publish recording events."""
        mock_event_store.is_paused = True

        controller.start()

        assert mock_event_bus.publish.called

    def test_stop_publishes_events(self, controller, mock_event_store, mock_event_bus):
        """stop() should publish recording events."""
        mock_event_store.is_recording = True

        controller.stop()

        assert mock_event_bus.publish.called
