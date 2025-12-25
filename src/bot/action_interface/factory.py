"""Factory functions for creating BotActionInterface instances."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.ui_controller import BotUIController
    from core.game_state import GameState
    from core.trade_manager import TradeManager
    from services.event_bus import EventBus
    from services.live_state_provider import LiveStateProvider

from .confirmation.monitor import ConfirmationMonitor
from .executors.simulated import SimulatedExecutor
from .executors.tkinter import TkinterExecutor
from .interface import BotActionInterface
from .state.tracker import StateTracker
from .types import ExecutionMode


def create_for_training(
    game_state: "GameState",
    trade_manager: "TradeManager",
    event_bus: "EventBus",
    simulated_latency_ms: int = 0,
) -> BotActionInterface:
    """
    Create BotActionInterface for TRAINING mode.

    Uses SimulatedExecutor for fastest execution.
    No confirmation monitoring - instant results.

    Args:
        game_state: GameState instance for state tracking
        trade_manager: TradeManager for simulated trade execution
        event_bus: EventBus instance for player action events
        simulated_latency_ms: Optional artificial latency (default 0ms)

    Returns:
        BotActionInterface configured for training mode
    """
    executor = SimulatedExecutor(
        game_state=game_state,
        trade_manager=trade_manager,
        simulated_latency_ms=simulated_latency_ms,
    )
    state_tracker = StateTracker(
        game_state=game_state,
        event_bus=event_bus,
    )

    return BotActionInterface(
        executor=executor,
        state_tracker=state_tracker,
        confirmation_monitor=None,
        mode=ExecutionMode.TRAINING,
    )


def create_for_recording(
    game_state: "GameState",
    live_state_provider: "LiveStateProvider",
    ui_controller: "BotUIController",
    event_bus: "EventBus",
) -> BotActionInterface:
    """
    Create BotActionInterface for RECORDING mode.

    Uses TkinterExecutor to intercept human clicks.
    Includes confirmation monitoring for latency tracking.

    Args:
        game_state: GameState instance for state tracking
        live_state_provider: LiveStateProvider for server-authoritative state
        ui_controller: BotUIController for UI interaction
        event_bus: EventBus for confirmation events

    Returns:
        BotActionInterface configured for recording mode
    """
    executor = TkinterExecutor(ui_controller=ui_controller, animate=True)
    state_tracker = StateTracker(
        game_state=game_state,
        event_bus=event_bus,
        live_state_provider=live_state_provider,
    )
    confirmation_monitor = ConfirmationMonitor(event_bus=event_bus)
    confirmation_monitor.start()

    return BotActionInterface(
        executor=executor,
        state_tracker=state_tracker,
        confirmation_monitor=confirmation_monitor,
        mode=ExecutionMode.RECORDING,
    )


def create_for_validation(
    game_state: "GameState",
    ui_controller: "BotUIController",
    event_bus: "EventBus",
) -> BotActionInterface:
    """
    Create BotActionInterface for VALIDATION mode.

    Uses TkinterExecutor to animate model decisions.
    No confirmation monitoring - replay from recorded data.

    Args:
        game_state: GameState instance for state tracking
        ui_controller: BotUIController for UI interaction
        event_bus: EventBus instance for player action events

    Returns:
        BotActionInterface configured for validation mode
    """
    executor = TkinterExecutor(ui_controller=ui_controller, animate=True)
    state_tracker = StateTracker(
        game_state=game_state,
        event_bus=event_bus,
    )

    return BotActionInterface(
        executor=executor,
        state_tracker=state_tracker,
        confirmation_monitor=None,
        mode=ExecutionMode.VALIDATION,
    )


def create_for_live(
    game_state: "GameState",
    live_state_provider: "LiveStateProvider",
    ui_controller: "BotUIController",  # For v1.0, use TkinterExecutor; v2.0 will use PuppeteerExecutor
    event_bus: "EventBus",
) -> BotActionInterface:
    """
    Create BotActionInterface for LIVE mode.

    v1.0: Uses TkinterExecutor (stub for PuppeteerExecutor)
    v2.0: Will use PuppeteerExecutor for real browser automation

    Args:
        game_state: GameState instance for state tracking
        live_state_provider: LiveStateProvider for server-authoritative state
        ui_controller: BotUIController for UI interaction (v1.0)
        event_bus: EventBus for confirmation events

    Returns:
        BotActionInterface configured for live mode
    """
    executor = TkinterExecutor(ui_controller=ui_controller, animate=False)
    state_tracker = StateTracker(
        game_state=game_state,
        event_bus=event_bus,
        live_state_provider=live_state_provider,
    )
    confirmation_monitor = ConfirmationMonitor(event_bus=event_bus)
    confirmation_monitor.start()

    return BotActionInterface(
        executor=executor,
        state_tracker=state_tracker,
        confirmation_monitor=confirmation_monitor,
        mode=ExecutionMode.LIVE,
    )
