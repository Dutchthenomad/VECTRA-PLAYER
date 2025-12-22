"""
Tests for Capture Stats Panel (Phase 12D)

Tests the capture stats display in the status bar:
- Session ID display (truncated to 8 chars)
- Event count display
- Periodic updates
"""

import tkinter as tk
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from services.event_bus import EventBus
from services.event_store import EventStoreService
from ui.builders.status_bar_builder import StatusBarBuilder


@pytest.fixture
def root():
    """Create a Tk root window for testing"""
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    root.destroy()


@pytest.fixture
def event_bus():
    """Create EventBus instance"""
    return EventBus()


class TestStatusBarBuilderCaptureStats:
    """Tests for capture stats in StatusBarBuilder"""

    def test_build_creates_capture_stats_label(self, root):
        """build() should create capture_stats_label"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert "capture_stats_label" in widgets
        assert isinstance(widgets["capture_stats_label"], tk.Label)

    def test_capture_stats_label_initial_text(self, root):
        """capture_stats_label should have initial text with dashes"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        text = widgets["capture_stats_label"].cget("text")
        assert "Session:" in text
        assert "Events:" in text
        assert "--------" in text or "0" in text

    def test_capture_stats_label_font(self, root):
        """capture_stats_label should use Courier font"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        font = widgets["capture_stats_label"].cget("font")
        # Font can be returned as tuple or string
        assert "Courier" in str(font)

    def test_capture_stats_label_background(self, root):
        """capture_stats_label should have a background color set"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        bg = widgets["capture_stats_label"].cget("bg")
        # Just verify a color is set (theme-dependent)
        assert bg is not None and len(bg) > 0

    def test_capture_stats_label_foreground(self, root):
        """capture_stats_label should have a foreground color set"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        fg = widgets["capture_stats_label"].cget("fg")
        # Just verify a color is set (theme-dependent)
        assert fg is not None and len(fg) > 0


class TestMainWindowCaptureStats:
    """Tests for capture stats updates in MainWindow"""

    @pytest.fixture
    def mock_main_window(self, root, event_bus):
        """Create a minimal mock MainWindow with required components"""
        from core.game_state import GameState

        # Create minimal MainWindow-like object
        window = MagicMock()
        window.root = root
        window.event_bus = event_bus
        window.state = GameState()

        # Create capture stats label (like StatusBarBuilder does)
        window.capture_stats_label = tk.Label(
            root,
            text="Session: -------- | Events: 0",
            font=("Courier", 9),
            bg="#000000",
            fg="#888888",
        )

        # Create EventStoreService
        window.event_store_service = EventStoreService(event_bus)

        return window

    def test_update_capture_stats_updates_session_id(self, mock_main_window):
        """_update_capture_stats should display truncated session ID"""
        from ui.main_window import MainWindow

        # Get the session ID (first 8 chars)
        session_id = mock_main_window.event_store_service.session_id[:8]

        # Manually call the update method
        MainWindow._update_capture_stats(mock_main_window)

        # Check label text contains session ID
        text = mock_main_window.capture_stats_label.cget("text")
        assert session_id in text
        assert "Session:" in text

    def test_update_capture_stats_updates_event_count(self, mock_main_window):
        """_update_capture_stats should display event count"""
        from ui.main_window import MainWindow

        # Initially should be 0
        MainWindow._update_capture_stats(mock_main_window)
        text = mock_main_window.capture_stats_label.cget("text")
        assert "Events: 0" in text

        # Simulate buffered events by mocking the writer's buffer_count property
        # Use PropertyMock to properly mock read-only properties
        with patch.object(
            type(mock_main_window.event_store_service._writer),
            "buffer_count",
            new_callable=PropertyMock,
            return_value=42,
        ):
            MainWindow._update_capture_stats(mock_main_window)
            text = mock_main_window.capture_stats_label.cget("text")
            assert "Events: 42" in text

    def test_update_capture_stats_format(self, mock_main_window):
        """_update_capture_stats should use correct format"""
        from ui.main_window import MainWindow

        session_id = mock_main_window.event_store_service.session_id[:8]

        MainWindow._update_capture_stats(mock_main_window)
        text = mock_main_window.capture_stats_label.cget("text")

        # Check format: "Session: <id> | Events: <count>"
        expected = f"Session: {session_id} | Events: 0"
        assert text == expected

    def test_update_capture_stats_handles_missing_service(self, mock_main_window):
        """_update_capture_stats should handle missing EventStoreService gracefully"""
        from ui.main_window import MainWindow

        # Remove the service
        mock_main_window.event_store_service = None

        # Should not raise exception
        MainWindow._update_capture_stats(mock_main_window)

        # Label should remain unchanged
        text = mock_main_window.capture_stats_label.cget("text")
        assert "Session:" in text  # Initial text preserved

    def test_update_capture_stats_schedules_next_update(self, mock_main_window):
        """_update_capture_stats should schedule next update after 1000ms"""
        from ui.main_window import MainWindow

        with patch.object(mock_main_window.root, "after") as mock_after:
            MainWindow._update_capture_stats(mock_main_window)

            # Should call root.after(1000, _update_capture_stats)
            mock_after.assert_called_once()
            args = mock_after.call_args[0]
            assert args[0] == 1000  # 1000ms interval
            assert callable(args[1])  # callback function

    def test_session_id_truncation(self, mock_main_window):
        """Session ID should be truncated to 8 characters"""
        from ui.main_window import MainWindow

        full_session_id = mock_main_window.event_store_service.session_id
        assert len(full_session_id) > 8  # UUID should be longer

        MainWindow._update_capture_stats(mock_main_window)
        text = mock_main_window.capture_stats_label.cget("text")

        # Extract session ID from text
        session_part = text.split("|")[0]  # "Session: abc12345 "
        displayed_id = session_part.split(":")[1].strip()

        assert len(displayed_id) == 8
        assert displayed_id == full_session_id[:8]

    def test_event_count_property_access(self, event_bus):
        """EventStoreService.event_count should return buffer count"""
        service = EventStoreService(event_bus)
        service.start()

        # Initially 0
        assert service.event_count == 0

        # After writing events (would increment buffer)
        # Note: We can't easily test this without publishing events,
        # but we verify the property exists and is accessible
        assert hasattr(service, "event_count")
        assert isinstance(service.event_count, int)

        service.stop()


class TestEventStoreServiceProperties:
    """Tests for EventStoreService properties used by capture stats"""

    def test_session_id_property(self, event_bus):
        """EventStoreService should expose session_id property"""
        service = EventStoreService(event_bus)
        assert hasattr(service, "session_id")
        assert isinstance(service.session_id, str)
        assert len(service.session_id) > 0

    def test_event_count_property(self, event_bus):
        """EventStoreService should expose event_count property"""
        service = EventStoreService(event_bus)
        assert hasattr(service, "event_count")
        assert isinstance(service.event_count, int)
        assert service.event_count >= 0

    def test_session_id_is_uuid(self, event_bus):
        """Session ID should be a valid UUID string"""
        import uuid

        service = EventStoreService(event_bus)

        # Should be parseable as UUID
        try:
            parsed = uuid.UUID(service.session_id)
            assert str(parsed) == service.session_id
        except ValueError:
            pytest.fail("session_id is not a valid UUID")

    def test_custom_session_id(self, event_bus):
        """EventStoreService should accept custom session_id"""
        custom_id = "test-session-12345678"
        service = EventStoreService(event_bus, session_id=custom_id)
        assert service.session_id == custom_id
