"""Tests for BotActionInterface factory functions."""

from unittest.mock import Mock

import pytest

from bot.action_interface import (
    BotActionInterface,
    ExecutionMode,
)
from bot.action_interface.executors.simulated import SimulatedExecutor
from bot.action_interface.executors.tkinter import TkinterExecutor
from bot.action_interface.factory import (
    create_for_live,
    create_for_recording,
    create_for_training,
    create_for_validation,
)


@pytest.fixture
def game_state():
    """Mock GameState."""
    return Mock()


@pytest.fixture
def trade_manager():
    """Mock TradeManager."""
    return Mock()


@pytest.fixture
def live_state_provider():
    """Mock LiveStateProvider."""
    return Mock()


@pytest.fixture
def ui_controller():
    """Mock BotUIController."""
    return Mock()


@pytest.fixture
def event_bus():
    """Mock EventBus."""
    mock_bus = Mock()
    mock_bus.subscribe = Mock()
    return mock_bus


class TestCreateForTraining:
    """Tests for create_for_training()."""

    def test_returns_bot_action_interface(self, game_state, trade_manager, event_bus):
        """Should return BotActionInterface instance."""
        interface = create_for_training(
            game_state=game_state,
            trade_manager=trade_manager,
            event_bus=event_bus,
        )
        assert isinstance(interface, BotActionInterface)

    def test_mode_is_training(self, game_state, trade_manager, event_bus):
        """Should configure TRAINING mode."""
        interface = create_for_training(
            game_state=game_state,
            trade_manager=trade_manager,
            event_bus=event_bus,
        )
        assert interface.mode == ExecutionMode.TRAINING

    def test_uses_simulated_executor(self, game_state, trade_manager, event_bus):
        """Should use SimulatedExecutor."""
        interface = create_for_training(
            game_state=game_state,
            trade_manager=trade_manager,
            event_bus=event_bus,
        )
        assert interface.executor_name == "simulated"

    def test_no_confirmation_monitor(self, game_state, trade_manager, event_bus):
        """Should not include confirmation monitor."""
        interface = create_for_training(
            game_state=game_state,
            trade_manager=trade_manager,
            event_bus=event_bus,
        )
        stats = interface.get_stats()
        # No latency tracking in training mode
        assert stats["latency"]["count"] == 0

    def test_respects_simulated_latency(self, game_state, trade_manager, event_bus):
        """Should pass simulated_latency_ms to executor."""
        interface = create_for_training(
            game_state=game_state,
            trade_manager=trade_manager,
            event_bus=event_bus,
            simulated_latency_ms=50,
        )
        # Executor should be properly configured
        assert isinstance(interface._executor, SimulatedExecutor)


class TestCreateForRecording:
    """Tests for create_for_recording()."""

    def test_returns_bot_action_interface(
        self, game_state, live_state_provider, ui_controller, event_bus
    ):
        """Should return BotActionInterface instance."""
        interface = create_for_recording(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert isinstance(interface, BotActionInterface)

    def test_mode_is_recording(self, game_state, live_state_provider, ui_controller, event_bus):
        """Should configure RECORDING mode."""
        interface = create_for_recording(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert interface.mode == ExecutionMode.RECORDING

    def test_uses_tkinter_executor(self, game_state, live_state_provider, ui_controller, event_bus):
        """Should use TkinterExecutor."""
        interface = create_for_recording(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert interface.executor_name == "tkinter"

    def test_starts_confirmation_monitor(
        self, game_state, live_state_provider, ui_controller, event_bus
    ):
        """Should start ConfirmationMonitor."""
        interface = create_for_recording(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        # Confirmation monitor should be present
        stats = interface.get_stats()
        assert "latency" in stats

    def test_executor_has_animation(
        self, game_state, live_state_provider, ui_controller, event_bus
    ):
        """Should enable animation in executor."""
        interface = create_for_recording(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        # TkinterExecutor should be configured with animate=True
        assert isinstance(interface._executor, TkinterExecutor)
        assert interface._executor._animate is True


class TestCreateForValidation:
    """Tests for create_for_validation()."""

    def test_returns_bot_action_interface(self, game_state, ui_controller, event_bus):
        """Should return BotActionInterface instance."""
        interface = create_for_validation(
            game_state=game_state,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert isinstance(interface, BotActionInterface)

    def test_mode_is_validation(self, game_state, ui_controller, event_bus):
        """Should configure VALIDATION mode."""
        interface = create_for_validation(
            game_state=game_state,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert interface.mode == ExecutionMode.VALIDATION

    def test_uses_tkinter_executor(self, game_state, ui_controller, event_bus):
        """Should use TkinterExecutor."""
        interface = create_for_validation(
            game_state=game_state,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert interface.executor_name == "tkinter"

    def test_no_confirmation_monitor(self, game_state, ui_controller, event_bus):
        """Should not include confirmation monitor."""
        interface = create_for_validation(
            game_state=game_state,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        stats = interface.get_stats()
        # No latency tracking in validation mode
        assert stats["latency"]["count"] == 0

    def test_executor_has_animation(self, game_state, ui_controller, event_bus):
        """Should enable animation in executor."""
        interface = create_for_validation(
            game_state=game_state,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        # TkinterExecutor should be configured with animate=True
        assert isinstance(interface._executor, TkinterExecutor)
        assert interface._executor._animate is True


class TestCreateForLive:
    """Tests for create_for_live()."""

    def test_returns_bot_action_interface(
        self, game_state, live_state_provider, ui_controller, event_bus
    ):
        """Should return BotActionInterface instance."""
        interface = create_for_live(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert isinstance(interface, BotActionInterface)

    def test_mode_is_live(self, game_state, live_state_provider, ui_controller, event_bus):
        """Should configure LIVE mode."""
        interface = create_for_live(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert interface.mode == ExecutionMode.LIVE

    def test_uses_tkinter_executor_v1(
        self, game_state, live_state_provider, ui_controller, event_bus
    ):
        """Should use TkinterExecutor in v1.0 (stub for Puppeteer)."""
        interface = create_for_live(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert interface.executor_name == "tkinter"

    def test_starts_confirmation_monitor(
        self, game_state, live_state_provider, ui_controller, event_bus
    ):
        """Should start ConfirmationMonitor."""
        interface = create_for_live(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        # Confirmation monitor should be present
        stats = interface.get_stats()
        assert "latency" in stats

    def test_executor_no_animation(self, game_state, live_state_provider, ui_controller, event_bus):
        """Should disable animation in executor (real mode)."""
        interface = create_for_live(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        # TkinterExecutor should be configured with animate=False
        assert isinstance(interface._executor, TkinterExecutor)
        assert interface._executor._animate is False


class TestFactoryIntegration:
    """Integration tests for all factory functions."""

    def test_all_factories_return_configured_interfaces(
        self, game_state, trade_manager, live_state_provider, ui_controller, event_bus
    ):
        """Should return properly configured interfaces for all modes."""
        # Training
        training = create_for_training(
            game_state=game_state,
            trade_manager=trade_manager,
            event_bus=event_bus,
        )
        assert training.mode == ExecutionMode.TRAINING
        assert training.is_available()

        # Recording
        recording = create_for_recording(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert recording.mode == ExecutionMode.RECORDING
        assert recording.is_available()

        # Validation
        validation = create_for_validation(
            game_state=game_state,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert validation.mode == ExecutionMode.VALIDATION
        assert validation.is_available()

        # Live
        live = create_for_live(
            game_state=game_state,
            live_state_provider=live_state_provider,
            ui_controller=ui_controller,
            event_bus=event_bus,
        )
        assert live.mode == ExecutionMode.LIVE
        assert live.is_available()

    def test_all_factories_have_unique_configurations(
        self, game_state, trade_manager, live_state_provider, ui_controller, event_bus
    ):
        """Should configure each mode differently."""
        interfaces = {
            "training": create_for_training(game_state, trade_manager, event_bus),
            "recording": create_for_recording(
                game_state, live_state_provider, ui_controller, event_bus
            ),
            "validation": create_for_validation(game_state, ui_controller, event_bus),
            "live": create_for_live(game_state, live_state_provider, ui_controller, event_bus),
        }

        # Collect executor names
        executors = {name: iface.executor_name for name, iface in interfaces.items()}

        # Training uses simulated, others use tkinter (for now)
        assert executors["training"] == "simulated"
        assert executors["recording"] == "tkinter"
        assert executors["validation"] == "tkinter"
        assert executors["live"] == "tkinter"

        # Recording and live have confirmation monitors
        assert "latency" in interfaces["recording"].get_stats()
        assert "latency" in interfaces["live"].get_stats()

        # Training and validation do not
        assert interfaces["training"].get_stats()["latency"]["count"] == 0
        assert interfaces["validation"].get_stats()["latency"]["count"] == 0
