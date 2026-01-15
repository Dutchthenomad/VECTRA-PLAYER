"""
Tests for MinimalWindow - Minimal UI for RL training data collection.

Tests verify:
- Window can be instantiated with required dependencies
- All expected widgets are created
- Button callbacks work without errors
- Status update methods work correctly
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest


class TestMinimalWindowInstantiation:
    """Test that MinimalWindow can be instantiated."""

    def test_minimal_window_creates_successfully(self, tk_root):
        """MinimalWindow should instantiate without errors."""
        from ui.minimal_window import MinimalWindow

        # Create mock dependencies
        mock_game_state = MagicMock()
        mock_game_state.get.return_value = Decimal("1.0")
        mock_event_bus = MagicMock()
        mock_config = MagicMock()

        # Instantiate window
        window = MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
            config=mock_config,
        )

        assert window is not None
        assert window.root == tk_root
        assert window.game_state == mock_game_state
        assert window.event_bus == mock_event_bus
        assert window.config == mock_config


class TestMinimalWindowWidgets:
    """Test that all expected widgets are created."""

    @pytest.fixture
    def minimal_window(self, tk_root):
        """Create a MinimalWindow instance for testing."""
        from ui.minimal_window import MinimalWindow

        mock_game_state = MagicMock()
        mock_game_state.get.return_value = Decimal("1.0")
        mock_event_bus = MagicMock()
        mock_config = MagicMock()

        return MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
            config=mock_config,
        )

    def test_status_labels_exist(self, minimal_window):
        """Status bar labels should be created."""
        assert minimal_window.tick_label is not None
        assert minimal_window.price_label is not None
        assert minimal_window.phase_label is not None
        assert minimal_window.connection_label is not None
        assert minimal_window.user_label is not None
        assert minimal_window.balance_label is not None

    def test_bet_entry_exists(self, minimal_window):
        """Bet entry widget should be created."""
        assert minimal_window.bet_entry is not None

    def test_percentage_buttons_exist(self, minimal_window):
        """Percentage buttons should be created (10%, 25%, 50%, 100%)."""
        assert len(minimal_window.percentage_buttons) == 4
        assert 0.1 in minimal_window.percentage_buttons
        assert 0.25 in minimal_window.percentage_buttons
        assert 0.5 in minimal_window.percentage_buttons
        assert 1.0 in minimal_window.percentage_buttons

    def test_default_sell_percentage_is_100(self, minimal_window):
        """Default sell percentage should be 100%."""
        assert minimal_window.current_sell_percentage == 1.0


class TestMinimalWindowCallbacks:
    """Test button callback methods."""

    @pytest.fixture
    def minimal_window(self, tk_root):
        """Create a MinimalWindow instance for testing."""
        from ui.minimal_window import MinimalWindow

        mock_game_state = MagicMock()
        mock_game_state.get.return_value = Decimal("10.0")
        mock_event_bus = MagicMock()
        mock_config = MagicMock()

        return MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
            config=mock_config,
        )

    def test_percentage_click_updates_current(self, minimal_window):
        """Clicking percentage button should update current_sell_percentage."""
        minimal_window._on_percentage_clicked(0.25)
        assert minimal_window.current_sell_percentage == 0.25

    def test_clear_click_resets_bet_entry(self, minimal_window):
        """Clicking clear should reset bet entry to 0."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "5.0")
        minimal_window._on_clear_clicked()
        # TradingController clears to "0", MinimalWindow fallback uses "0.000"
        assert minimal_window.bet_entry.get() in ("0", "0.000")

    def test_increment_click_adds_value(self, minimal_window):
        """Clicking increment should add value to bet entry."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "1.0")
        minimal_window._on_increment_clicked("+0.01")
        assert minimal_window.bet_entry.get() == "1.01"

    def test_utility_half_halves_value(self, minimal_window):
        """1/2 utility should halve the bet amount."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "2.0")
        minimal_window._on_utility_clicked("1/2")
        assert minimal_window.bet_entry.get() == "1.0"

    def test_utility_double_doubles_value(self, minimal_window):
        """X2 utility should double the bet amount."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "1.0")
        minimal_window._on_utility_clicked("X2")
        assert minimal_window.bet_entry.get() == "2.0"

    def test_utility_max_sets_balance(self, minimal_window):
        """MAX utility should set bet to balance from game_state."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "0.0")
        minimal_window._on_utility_clicked("MAX")
        assert minimal_window.bet_entry.get() == "10.0"

    def test_buy_click_does_not_error(self, minimal_window):
        """BUY click should not raise an error (placeholder)."""
        minimal_window._on_buy_clicked()  # Should not raise

    def test_sell_click_does_not_error(self, minimal_window):
        """SELL click should not raise an error (placeholder)."""
        minimal_window._on_sell_clicked()  # Should not raise

    def test_sidebet_click_does_not_error(self, minimal_window):
        """SIDEBET click should not raise an error (placeholder)."""
        minimal_window._on_sidebet_clicked()  # Should not raise


class TestMinimalWindowStatusUpdates:
    """Test status update methods."""

    @pytest.fixture
    def minimal_window(self, tk_root):
        """Create a MinimalWindow instance for testing."""
        from ui.minimal_window import MinimalWindow

        mock_game_state = MagicMock()
        mock_game_state.get.return_value = Decimal("1.0")
        mock_event_bus = MagicMock()
        mock_config = MagicMock()

        return MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
            config=mock_config,
        )

    def test_update_tick(self, minimal_window):
        """update_tick should update tick label."""
        minimal_window.update_tick(1234)
        assert minimal_window.tick_label.cget("text") == "1234"

    def test_update_price(self, minimal_window):
        """update_price should update price label."""
        minimal_window.update_price(123.45)
        assert minimal_window.price_label.cget("text") == "123.45"

    def test_update_phase_active(self, minimal_window):
        """update_phase should set text and color for ACTIVE."""
        minimal_window.update_phase("ACTIVE")
        assert minimal_window.phase_label.cget("text") == "ACTIVE"

    def test_update_phase_presale(self, minimal_window):
        """update_phase should set text for PRESALE."""
        minimal_window.update_phase("PRESALE")
        assert minimal_window.phase_label.cget("text") == "PRESALE"

    def test_update_connection_true(self, minimal_window):
        """update_connection True should show green dot."""
        minimal_window.update_connection(True)
        # Check that fg color changed (can't easily assert color in Tk)
        # Just verify it doesn't error

    def test_update_connection_false(self, minimal_window):
        """update_connection False should show gray dot."""
        minimal_window.update_connection(False)

    def test_update_user(self, minimal_window):
        """update_user should update user label."""
        minimal_window.update_user("TestPlayer")
        assert minimal_window.user_label.cget("text") == "TestPlayer"

    def test_update_user_empty(self, minimal_window):
        """update_user with empty string should show ---."""
        minimal_window.update_user("")
        assert minimal_window.user_label.cget("text") == "---"

    def test_update_balance(self, minimal_window):
        """update_balance should update balance label."""
        minimal_window.update_balance(Decimal("12.345"))
        assert minimal_window.balance_label.cget("text") == "12.345 SOL"


class TestMinimalWindowUtilityMethods:
    """Test utility methods."""

    @pytest.fixture
    def minimal_window(self, tk_root):
        """Create a MinimalWindow instance for testing."""
        from ui.minimal_window import MinimalWindow

        mock_game_state = MagicMock()
        mock_game_state.get.return_value = Decimal("1.0")
        mock_event_bus = MagicMock()
        mock_config = MagicMock()

        return MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
            config=mock_config,
        )

    def test_get_bet_amount(self, minimal_window):
        """get_bet_amount should return current bet entry value."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "5.5")
        assert minimal_window.get_bet_amount() == Decimal("5.5")

    def test_get_bet_amount_invalid_returns_zero(self, minimal_window):
        """get_bet_amount with invalid input should return 0."""
        minimal_window.bet_entry.delete(0, "end")
        minimal_window.bet_entry.insert(0, "invalid")
        assert minimal_window.get_bet_amount() == Decimal("0")

    def test_set_bet_amount(self, minimal_window):
        """set_bet_amount should update bet entry."""
        minimal_window.set_bet_amount(Decimal("7.77"))
        assert minimal_window.bet_entry.get() == "7.77"

    def test_get_sell_percentage(self, minimal_window):
        """get_sell_percentage should return current percentage."""
        minimal_window.current_sell_percentage = 0.5
        assert minimal_window.get_sell_percentage() == 0.5


class TestMinimalWindowTradingController:
    """Test TradingController integration (Task 2)."""

    @pytest.fixture
    def minimal_window_with_eventbus(self, tk_root):
        """Create MinimalWindow with real EventBus for testing ButtonEvent emission."""
        from services.event_bus import EventBus
        from ui.minimal_window import MinimalWindow

        # Create real EventBus (started)
        event_bus = EventBus()
        event_bus.start()

        mock_game_state = MagicMock()
        mock_game_state.get.side_effect = lambda key, default=None: {
            "current_tick": 42,
            "current_price": Decimal("1.5"),
            "game_id": "game-123",
            "current_phase": "ACTIVE",
            "balance": Decimal("10.0"),
            "position_qty": Decimal("0"),
        }.get(key, default)
        mock_game_state.set_sell_percentage.return_value = True

        mock_config = MagicMock()
        mock_config.FINANCIAL = {"min_bet": Decimal("0.001"), "max_bet": Decimal("100")}

        window = MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=event_bus,
            config=mock_config,
        )

        yield window, event_bus

        # Cleanup
        event_bus.stop()

    def test_trading_controller_created(self, minimal_window_with_eventbus):
        """TradingController should be created automatically."""
        window, _event_bus = minimal_window_with_eventbus
        assert window.trading_controller is not None

    def test_buy_click_emits_button_event(self, minimal_window_with_eventbus):
        """BUY click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click BUY
        window._on_buy_clicked()

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "BUY"
        assert received_events[0]["data"]["button_category"] == "action"
        assert "client_timestamp" in received_events[0]["data"]

    def test_sell_click_emits_button_event(self, minimal_window_with_eventbus):
        """SELL click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click SELL
        window._on_sell_clicked()

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "SELL"

    def test_sidebet_click_emits_button_event(self, minimal_window_with_eventbus):
        """SIDEBET click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click SIDEBET
        window._on_sidebet_clicked()

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "SIDEBET"

    def test_increment_click_emits_button_event(self, minimal_window_with_eventbus):
        """Increment button click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click increment +0.01
        window._on_increment_clicked("+0.01")

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "INC_01"
        assert received_events[0]["data"]["button_category"] == "bet_adjust"

    def test_utility_half_emits_button_event(self, minimal_window_with_eventbus):
        """1/2 utility button click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Set initial bet amount
        window.bet_entry.delete(0, "end")
        window.bet_entry.insert(0, "2.0")

        # Click 1/2
        window._on_utility_clicked("1/2")

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "HALF"

    def test_clear_click_emits_button_event(self, minimal_window_with_eventbus):
        """Clear (X) button click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click clear
        window._on_clear_clicked()

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "CLEAR"

    def test_percentage_click_emits_button_event(self, minimal_window_with_eventbus):
        """Percentage button click should emit BUTTON_PRESS event."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click 25%
        window._on_percentage_clicked(0.25)

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "SELL_25"
        assert received_events[0]["data"]["button_category"] == "percentage"

    def test_button_event_contains_game_context(self, minimal_window_with_eventbus):
        """ButtonEvent should contain full game context."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Click BUY
        window._on_buy_clicked()

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        event_data = received_events[0]["data"]

        # Check game context fields
        assert event_data["tick"] == 42
        assert event_data["game_phase"] == 2  # ACTIVE
        assert event_data["game_id"] == "game-123"
        assert "sequence_id" in event_data
        assert "sequence_position" in event_data

    def test_button_event_contains_client_timestamp(self, minimal_window_with_eventbus):
        """ButtonEvent should contain client_timestamp for latency tracking."""
        import time

        from services.event_bus import Events

        window, event_bus = minimal_window_with_eventbus
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        before_ts = int(time.time() * 1000)
        window._on_buy_clicked()
        after_ts = int(time.time() * 1000)

        # Wait for async event processing
        time.sleep(0.2)

        assert len(received_events) == 1
        client_ts = received_events[0]["data"]["client_timestamp"]

        # Timestamp should be within the test window
        assert before_ts <= client_ts <= after_ts + 100  # Allow 100ms tolerance


class TestMinimalWindowEventSubscriptions:
    """Test Task 3: WebSocket event subscriptions and UI updates.

    Note: These tests verify the event handler logic directly rather than
    through the EventBus, since root.after() cannot be tested reliably in
    a non-main-loop environment. The integration with EventBus is tested
    separately through subscription verification tests.
    """

    @pytest.fixture
    def minimal_window_with_real_eventbus(self, tk_root):
        """Create MinimalWindow with real EventBus for event subscription testing."""
        from services.event_bus import EventBus
        from ui.minimal_window import MinimalWindow

        # Create real EventBus (started)
        event_bus = EventBus()
        event_bus.start()

        mock_game_state = MagicMock()
        mock_game_state.get.side_effect = lambda key, default=None: {
            "current_tick": 0,
            "current_price": Decimal("1.0"),
            "game_id": "game-000",
            "current_phase": "UNKNOWN",
            "balance": Decimal("0.0"),
            "position_qty": Decimal("0"),
        }.get(key, default)
        mock_game_state.set_sell_percentage.return_value = True

        mock_config = MagicMock()
        mock_config.FINANCIAL = {"min_bet": Decimal("0.001"), "max_bet": Decimal("100")}

        window = MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=event_bus,
            config=mock_config,
        )

        yield window, event_bus

        # Cleanup
        window._unsubscribe_from_events()
        event_bus.stop()

    def test_event_subscriptions_registered(self, minimal_window_with_real_eventbus):
        """MinimalWindow should subscribe to required events on init."""
        from services.event_bus import Events

        _window, event_bus = minimal_window_with_real_eventbus

        # Verify subscriptions exist
        assert event_bus.has_subscribers(Events.WS_RAW_EVENT)
        assert event_bus.has_subscribers(Events.WS_CONNECTED)
        assert event_bus.has_subscribers(Events.WS_DISCONNECTED)
        assert event_bus.has_subscribers(Events.PLAYER_UPDATE)

    def test_handle_game_state_update_tick(self, minimal_window_with_real_eventbus):
        """_handle_game_state_update should schedule tick label update."""
        window, _event_bus = minimal_window_with_real_eventbus

        # Call handler directly (simulating what happens in _on_ws_raw_event)
        event_data = {
            "tickCount": 1234,
            "multiplier": 5.67,
            "active": True,
            "rugged": False,
        }
        window._handle_game_state_update(event_data)

        # Process pending Tk events to execute root.after() callbacks
        window.root.update()

        assert window.tick_label.cget("text") == "1234"

    def test_handle_game_state_update_price(self, minimal_window_with_real_eventbus):
        """_handle_game_state_update should schedule price label update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {
            "tickCount": 100,
            "multiplier": 123.45,
            "active": True,
            "rugged": False,
        }
        window._handle_game_state_update(event_data)
        window.root.update()

        assert window.price_label.cget("text") == "123.45"

    def test_handle_game_state_update_phase_active(self, minimal_window_with_real_eventbus):
        """_handle_game_state_update should schedule ACTIVE phase update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {
            "tickCount": 100,
            "multiplier": 1.0,
            "active": True,
            "rugged": False,
        }
        window._handle_game_state_update(event_data)
        window.root.update()

        assert window.phase_label.cget("text") == "ACTIVE"

    def test_handle_game_state_update_phase_presale(self, minimal_window_with_real_eventbus):
        """_handle_game_state_update should schedule PRESALE phase update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {
            "tickCount": 0,
            "multiplier": 1.0,
            "active": False,
            "rugged": False,
            "allowPreRoundBuys": True,
        }
        window._handle_game_state_update(event_data)
        window.root.update()

        assert window.phase_label.cget("text") == "PRESALE"

    def test_handle_game_state_update_phase_cooldown(self, minimal_window_with_real_eventbus):
        """_handle_game_state_update should schedule COOLDOWN phase update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {
            "tickCount": 0,
            "multiplier": 1.0,
            "active": False,
            "rugged": False,
            "cooldownTimer": 5,
        }
        window._handle_game_state_update(event_data)
        window.root.update()

        assert window.phase_label.cget("text") == "COOLDOWN"

    def test_handle_game_state_update_phase_rugged(self, minimal_window_with_real_eventbus):
        """_handle_game_state_update should schedule RUGGED phase update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {
            "tickCount": 150,
            "multiplier": 50.0,
            "active": True,
            "rugged": True,
        }
        window._handle_game_state_update(event_data)
        window.root.update()

        assert window.phase_label.cget("text") == "RUGGED"

    def test_handle_username_status(self, minimal_window_with_real_eventbus):
        """_handle_username_status should schedule user label update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {"username": "TestPlayer123"}
        window._handle_username_status(event_data)
        window.root.update()

        assert window.user_label.cget("text") == "TestPlayer123"

    def test_handle_player_update_raw(self, minimal_window_with_real_eventbus):
        """_handle_player_update_raw should schedule balance label update."""
        window, _event_bus = minimal_window_with_real_eventbus

        event_data = {"cash": 12.345}
        window._handle_player_update_raw(event_data)
        window.root.update()

        assert window.balance_label.cget("text") == "12.345 SOL"

    def test_on_player_update(self, minimal_window_with_real_eventbus):
        """_on_player_update should schedule balance label update."""
        window, _event_bus = minimal_window_with_real_eventbus

        # Simulating EventBus wrapped format
        wrapped = {"name": "player.update", "data": {"cash": 99.999}}
        window._on_player_update(wrapped)
        window.root.update()

        assert window.balance_label.cget("text") == "99.999 SOL"

    def test_on_ws_connected(self, minimal_window_with_real_eventbus):
        """_on_ws_connected should schedule connection indicator to green."""
        window, _event_bus = minimal_window_with_real_eventbus

        # First set to disconnected
        window.update_connection(False)
        window.root.update()

        # Call connected handler
        window._on_ws_connected({})
        window.root.update()

        fg_color = window.connection_label.cget("fg")
        assert fg_color == "#00ff66"  # GREEN_COLOR

    def test_on_ws_disconnected(self, minimal_window_with_real_eventbus):
        """_on_ws_disconnected should schedule connection indicator to gray."""
        window, _event_bus = minimal_window_with_real_eventbus

        # First set to connected
        window.update_connection(True)
        window.root.update()

        # Call disconnected handler
        window._on_ws_disconnected({})
        window.root.update()

        fg_color = window.connection_label.cget("fg")
        assert fg_color == "#666666"  # GRAY_COLOR

    def test_on_ws_raw_event_game_state_update(self, minimal_window_with_real_eventbus):
        """_on_ws_raw_event should route gameStateUpdate events correctly."""
        window, _event_bus = minimal_window_with_real_eventbus

        wrapped = {
            "name": "ws.raw_event",
            "data": {
                "event": "gameStateUpdate",
                "data": {
                    "tickCount": 999,
                    "multiplier": 77.77,
                    "active": True,
                    "rugged": False,
                },
            },
        }
        window._on_ws_raw_event(wrapped)
        window.root.update()

        assert window.tick_label.cget("text") == "0999"
        assert window.price_label.cget("text") == "77.77"
        assert window.phase_label.cget("text") == "ACTIVE"

    def test_on_ws_raw_event_username_status(self, minimal_window_with_real_eventbus):
        """_on_ws_raw_event should route usernameStatus events correctly."""
        window, _event_bus = minimal_window_with_real_eventbus

        wrapped = {
            "name": "ws.raw_event",
            "data": {
                "event": "usernameStatus",
                "data": {"username": "RealPlayer"},
            },
        }
        window._on_ws_raw_event(wrapped)
        window.root.update()

        assert window.user_label.cget("text") == "RealPlayer"

    def test_on_ws_raw_event_player_update(self, minimal_window_with_real_eventbus):
        """_on_ws_raw_event should route playerUpdate events correctly."""
        window, _event_bus = minimal_window_with_real_eventbus

        wrapped = {
            "name": "ws.raw_event",
            "data": {
                "event": "playerUpdate",
                "data": {"cash": 55.555},
            },
        }
        window._on_ws_raw_event(wrapped)
        window.root.update()

        assert window.balance_label.cget("text") == "55.555 SOL"


class TestMinimalWindowPhaseDetection:
    """Test the _detect_phase static method."""

    def test_detect_phase_cooldown_timer(self):
        """cooldownTimer > 0 should return COOLDOWN."""
        from ui.minimal_window import MinimalWindow

        result = MinimalWindow._detect_phase({"cooldownTimer": 5})
        assert result == "COOLDOWN"

    def test_detect_phase_cooldown_rugged_not_active(self):
        """rugged=True and active=False should return COOLDOWN."""
        from ui.minimal_window import MinimalWindow

        result = MinimalWindow._detect_phase({"rugged": True, "active": False})
        assert result == "COOLDOWN"

    def test_detect_phase_presale(self):
        """allowPreRoundBuys=True and active=False should return PRESALE."""
        from ui.minimal_window import MinimalWindow

        result = MinimalWindow._detect_phase({"allowPreRoundBuys": True, "active": False})
        assert result == "PRESALE"

    def test_detect_phase_active(self):
        """active=True and rugged=False should return ACTIVE."""
        from ui.minimal_window import MinimalWindow

        result = MinimalWindow._detect_phase({"active": True, "rugged": False})
        assert result == "ACTIVE"

    def test_detect_phase_rugged(self):
        """rugged=True and active=True should return RUGGED."""
        from ui.minimal_window import MinimalWindow

        result = MinimalWindow._detect_phase({"active": True, "rugged": True})
        assert result == "RUGGED"

    def test_detect_phase_unknown(self):
        """Empty dict should return UNKNOWN."""
        from ui.minimal_window import MinimalWindow

        result = MinimalWindow._detect_phase({})
        assert result == "UNKNOWN"

    def test_detect_phase_cooldown_takes_priority(self):
        """cooldownTimer takes priority over other flags."""
        from ui.minimal_window import MinimalWindow

        # Even with active=True, cooldownTimer > 0 means COOLDOWN
        result = MinimalWindow._detect_phase({"cooldownTimer": 3, "active": True})
        assert result == "COOLDOWN"


class TestRecordingToggle:
    """Test recording toggle functionality (Task 4: 1-click recording toggle)."""

    @pytest.fixture
    def minimal_window_with_event_store(self, tk_root):
        """Create MinimalWindow with mock EventStore for testing recording toggle."""
        from services.event_bus import EventBus
        from ui.minimal_window import MinimalWindow

        # Create real EventBus (started)
        event_bus = EventBus()
        event_bus.start()

        mock_game_state = MagicMock()
        mock_game_state.get.side_effect = lambda key, default=None: {
            "current_tick": 0,
            "current_price": Decimal("1.0"),
            "game_id": "game-000",
            "current_phase": "UNKNOWN",
            "balance": Decimal("0.0"),
            "position_qty": Decimal("0"),
        }.get(key, default)
        mock_game_state.set_sell_percentage.return_value = True

        mock_config = MagicMock()
        mock_config.FINANCIAL = {"min_bet": Decimal("0.001"), "max_bet": Decimal("100")}

        # Create mock EventStore
        mock_event_store = MagicMock()
        mock_event_store.is_recording = False
        mock_event_store.is_paused = True
        mock_event_store.event_count = 0
        mock_event_store.recorded_game_ids = set()

        # toggle_recording returns new state
        def toggle_recording():
            mock_event_store.is_recording = not mock_event_store.is_recording
            mock_event_store.is_paused = not mock_event_store.is_recording
            return mock_event_store.is_recording

        mock_event_store.toggle_recording.side_effect = toggle_recording

        window = MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=event_bus,
            config=mock_config,
            event_store=mock_event_store,
        )

        yield window, event_bus, mock_event_store

        # Cleanup
        window._unsubscribe_from_events()
        event_bus.stop()

    def test_recording_toggle_exists(self, minimal_window_with_event_store):
        """Recording toggle should exist when event_store is provided."""
        window, _event_bus, _mock_event_store = minimal_window_with_event_store
        assert hasattr(window, "recording_toggle")
        assert window.recording_toggle is not None

    def test_recording_toggle_initial_state_off(self, minimal_window_with_event_store):
        """Recording toggle should be OFF initially (not recording)."""
        window, _event_bus, _mock_event_store = minimal_window_with_event_store
        assert window.recording_toggle.is_recording is False

    def test_recording_toggle_click_toggles_recording(self, minimal_window_with_event_store):
        """Clicking recording toggle should toggle recording state."""
        window, _event_bus, mock_event_store = minimal_window_with_event_store

        # Initially not recording
        assert mock_event_store.is_recording is False

        # Toggle recording
        window._on_rec_toggled()
        window.root.update()

        # Should be recording now
        assert mock_event_store.toggle_recording.called

    def test_recording_toggle_turns_on_when_recording(self, minimal_window_with_event_store):
        """Recording toggle should show ON state when recording is active."""
        window, _event_bus, _mock_event_store = minimal_window_with_event_store

        # Update visual state to recording
        window.update_recording_state(is_recording=True)
        window.root.update()

        assert window.recording_toggle.is_recording is True

    def test_recording_toggle_turns_off_when_stopped(self, minimal_window_with_event_store):
        """Recording toggle should show OFF state when recording is stopped."""
        window, _event_bus, _mock_event_store = minimal_window_with_event_store

        # First turn on
        window.update_recording_state(is_recording=True)
        window.root.update()

        # Then turn off
        window.update_recording_state(is_recording=False)
        window.root.update()

        assert window.recording_toggle.is_recording is False

    def test_recording_toggle_subscribes_to_recording_toggled(
        self, minimal_window_with_event_store
    ):
        """MinimalWindow should subscribe to RECORDING_TOGGLED event."""
        from services.event_bus import Events

        _window, event_bus, _mock_event_store = minimal_window_with_event_store
        assert event_bus.has_subscribers(Events.RECORDING_TOGGLED)

    def test_recording_toggled_event_updates_toggle(self, minimal_window_with_event_store):
        """RECORDING_TOGGLED event handler should update recording toggle visual state.

        Note: We test the handler directly because root.after() doesn't work
        from non-main threads in tests. The subscription is verified separately.
        """
        window, _event_bus, _mock_event_store = minimal_window_with_event_store

        # Simulate what the event handler does (call update directly)
        window.update_recording_state(is_recording=True)
        window.root.update()

        assert window.recording_toggle.is_recording is True

    def test_recording_controller_created_with_event_store(self, minimal_window_with_event_store):
        """RecordingController should be created when event_store is provided."""
        window, _event_bus, _mock_event_store = minimal_window_with_event_store
        assert hasattr(window, "recording_controller")
        assert window.recording_controller is not None

    def test_no_recording_toggle_without_event_store(self, tk_root):
        """No recording toggle should exist when event_store is not provided."""
        from ui.minimal_window import MinimalWindow

        mock_game_state = MagicMock()
        mock_game_state.get.return_value = Decimal("1.0")
        mock_event_bus = MagicMock()
        mock_config = MagicMock()

        window = MinimalWindow(
            root=tk_root,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
            config=mock_config,
            # No event_store provided
        )

        # recording_toggle should be None when no event_store
        assert window.recording_toggle is None
        assert window.recording_controller is None


# Fixture for Tk root (shared with conftest.py)
@pytest.fixture
def tk_root():
    """Create and clean up a Tk root window for testing."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()  # Hide window during tests
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass  # Window already destroyed
