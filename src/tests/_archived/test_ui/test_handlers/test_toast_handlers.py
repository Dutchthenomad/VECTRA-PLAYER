"""
Tests for ToastHandlersMixin.

Issue #138: Migrate Toast Notifications to Socket Events
"""

import time

from services.event_bus import EventBus, Events
from ui.handlers.toast_handlers import ToastHandlersMixin


class MockToast:
    """Mock toast notification widget."""

    def __init__(self):
        self.messages = []

    def show(self, message: str, msg_type: str = "info"):
        self.messages.append((message, msg_type))


class MockUiDispatcher:
    """Mock UI dispatcher that executes immediately."""

    def submit(self, callback):
        callback()


class MockConfig:
    """Mock config object."""

    TOAST_PREFERENCES = {
        "ws_connected": True,
        "ws_disconnected": True,
        "ws_error": True,
        "game_start": True,
        "game_end": True,
        "game_rug": True,
    }


class ToastHandlerHost(ToastHandlersMixin):
    """Test host class that includes ToastHandlersMixin."""

    def __init__(self, event_bus: EventBus, config=None):
        self.event_bus = event_bus
        self.config = config or MockConfig()
        self.toast = MockToast()
        self.ui_dispatcher = MockUiDispatcher()


class TestToastHandlersMixinSetup:
    """Tests for ToastHandlersMixin setup."""

    def test_setup_toast_handlers_registers_ws_events(self):
        """Verify WebSocket event handlers are registered."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Verify subscriptions exist
            assert event_bus.has_subscribers(Events.WS_CONNECTED)
            assert event_bus.has_subscribers(Events.WS_DISCONNECTED)
            assert event_bus.has_subscribers(Events.WS_ERROR)
        finally:
            event_bus.stop()

    def test_setup_toast_handlers_registers_game_events(self):
        """Verify game lifecycle event handlers are registered."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Verify subscriptions exist
            assert event_bus.has_subscribers(Events.GAME_START)
            assert event_bus.has_subscribers(Events.GAME_END)
            assert event_bus.has_subscribers(Events.GAME_RUG)
        finally:
            event_bus.stop()


class TestToastHandlersMixinWebSocketEvents:
    """Tests for WebSocket event toast handling."""

    def test_ws_connected_shows_toast(self):
        """WS_CONNECTED event should show success toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish event
            event_bus.publish(Events.WS_CONNECTED, {"source": "live feed"})
            time.sleep(0.2)  # Allow event processing

            # Verify toast was shown
            assert len(host.toast.messages) == 1
            message, msg_type = host.toast.messages[0]
            assert "Connected" in message
            assert "live feed" in message
            assert msg_type == "success"
        finally:
            event_bus.stop()

    def test_ws_disconnected_shows_toast(self):
        """WS_DISCONNECTED event should show warning toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish event
            event_bus.publish(Events.WS_DISCONNECTED, {"reason": "server closed"})
            time.sleep(0.2)

            # Verify toast was shown
            assert len(host.toast.messages) == 1
            message, msg_type = host.toast.messages[0]
            assert "Disconnected" in message
            assert msg_type == "warning"
        finally:
            event_bus.stop()

    def test_ws_error_shows_toast(self):
        """WS_ERROR event should show error toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish event
            event_bus.publish(Events.WS_ERROR, {"error": "Connection timeout"})
            time.sleep(0.2)

            # Verify toast was shown
            assert len(host.toast.messages) == 1
            message, msg_type = host.toast.messages[0]
            assert "Connection timeout" in message
            assert msg_type == "error"
        finally:
            event_bus.stop()


class TestToastHandlersMixinGameEvents:
    """Tests for game lifecycle event toast handling."""

    def test_game_start_shows_toast(self):
        """GAME_START event should show info toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish event
            event_bus.publish(Events.GAME_START, {"game_id": "abc12345"})
            time.sleep(0.2)

            # Verify toast was shown
            assert len(host.toast.messages) == 1
            message, msg_type = host.toast.messages[0]
            assert "game started" in message.lower()
            assert msg_type == "info"
        finally:
            event_bus.stop()

    def test_game_end_shows_toast_for_non_rug(self):
        """GAME_END event (non-rug) should show info toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish non-rug game end
            event_bus.publish(Events.GAME_END, {"final_price": 5.5, "rugged": False})
            time.sleep(0.2)

            # Verify toast was shown
            assert len(host.toast.messages) == 1
            message, msg_type = host.toast.messages[0]
            assert "ended" in message.lower()
            assert "5.50x" in message
            assert msg_type == "info"
        finally:
            event_bus.stop()

    def test_game_end_skips_toast_for_rug(self):
        """GAME_END event with rugged=True should not show toast (GAME_RUG handles it)."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish rugged game end
            event_bus.publish(Events.GAME_END, {"final_price": 2.0, "rugged": True})
            time.sleep(0.2)

            # Verify no toast was shown (GAME_RUG handler handles rugged games)
            assert len(host.toast.messages) == 0
        finally:
            event_bus.stop()

    def test_game_rug_shows_error_toast(self):
        """GAME_RUG event should show error toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            host = ToastHandlerHost(event_bus)
            host._setup_toast_handlers()

            # Publish rug event
            event_bus.publish(Events.GAME_RUG, {"price": 3.2})
            time.sleep(0.2)

            # Verify toast was shown
            assert len(host.toast.messages) == 1
            message, msg_type = host.toast.messages[0]
            assert "RUGGED" in message
            assert "3.20x" in message
            assert msg_type == "error"
        finally:
            event_bus.stop()


class TestToastHandlersMixinPreferences:
    """Tests for toast preferences."""

    def test_disabled_preference_skips_toast(self):
        """Disabled toast preference should skip showing toast."""
        event_bus = EventBus()
        event_bus.start()
        try:
            # Create host with ws_connected disabled
            config = MockConfig()
            config.TOAST_PREFERENCES = {"ws_connected": False}
            host = ToastHandlerHost(event_bus, config)
            host._setup_toast_handlers()

            # Publish event
            event_bus.publish(Events.WS_CONNECTED, {"source": "live feed"})
            time.sleep(0.2)

            # Verify no toast was shown
            assert len(host.toast.messages) == 0
        finally:
            event_bus.stop()

    def test_set_toast_preference(self):
        """set_toast_preference should update preferences."""
        event_bus = EventBus()
        host = ToastHandlerHost(event_bus)
        host._setup_toast_handlers()

        # Initially enabled
        assert host._is_toast_enabled("ws_connected")

        # Disable
        host.set_toast_preference("ws_connected", False)
        assert not host._is_toast_enabled("ws_connected")

        # Re-enable
        host.set_toast_preference("ws_connected", True)
        assert host._is_toast_enabled("ws_connected")

    def test_get_toast_preferences_returns_copy(self):
        """get_toast_preferences should return a copy to prevent mutation."""
        event_bus = EventBus()
        host = ToastHandlerHost(event_bus)
        host._setup_toast_handlers()

        prefs1 = host.get_toast_preferences()
        prefs2 = host.get_toast_preferences()

        # Should be equal but not same object
        assert prefs1 == prefs2
        assert prefs1 is not prefs2


class TestToastHandlersMixinThreadSafety:
    """Tests for thread-safe toast display."""

    def test_show_toast_safe_uses_dispatcher(self):
        """_show_toast_safe should use ui_dispatcher for thread safety."""
        event_bus = EventBus()
        host = ToastHandlerHost(event_bus)

        # Replace dispatcher with one that tracks calls
        dispatcher_calls = []

        class TrackingDispatcher:
            def submit(self, callback):
                dispatcher_calls.append(callback)
                callback()

        host.ui_dispatcher = TrackingDispatcher()
        host._setup_toast_handlers()

        # Show toast
        host._show_toast_safe("Test message", "info")

        # Verify dispatcher was used
        assert len(dispatcher_calls) == 1

    def test_show_toast_safe_handles_missing_toast(self):
        """_show_toast_safe should handle missing toast widget gracefully."""
        event_bus = EventBus()
        host = ToastHandlerHost(event_bus)
        host.toast = None  # Simulate uninitialized toast
        host._setup_toast_handlers()

        # Should not raise
        host._show_toast_safe("Test message", "info")
