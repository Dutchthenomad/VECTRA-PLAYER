"""
BotActionInterface - Main orchestrator for unified action execution.

Coordinates:
- Executor selection (Tkinter/Simulated/Puppeteer)
- State capture before/after via StateTracker
- Confirmation monitoring via ConfirmationMonitor
- Event emission for persistence
"""

import logging
import time
import uuid
from typing import TYPE_CHECKING

from .types import ActionParams, ActionResult, ExecutionMode

if TYPE_CHECKING:
    from .confirmation.monitor import ConfirmationMonitor
    from .executors.base import ActionExecutor
    from .state.tracker import StateTracker

logger = logging.getLogger(__name__)


class BotActionInterface:
    """
    Unified API for action execution across all modes.

    Coordinates:
    - Executor selection
    - State capture (before/after)
    - Confirmation monitoring
    - Event emission for persistence

    Usage:
        # Training mode (fast simulated)
        interface = BotActionInterface(
            executor=SimulatedExecutor(trade_manager),
            state_tracker=StateTracker(game_state, event_bus),
            mode=ExecutionMode.TRAINING,
        )

        # Live mode (real browser with confirmation monitoring)
        interface = BotActionInterface(
            executor=PuppeteerExecutor(browser_controller),
            state_tracker=StateTracker(game_state, event_bus, live_state_provider),
            confirmation_monitor=ConfirmationMonitor(event_bus),
            mode=ExecutionMode.LIVE,
        )

        # Execute action
        result = await interface.execute(
            ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        )
    """

    def __init__(
        self,
        executor: "ActionExecutor",
        state_tracker: "StateTracker",
        confirmation_monitor: "ConfirmationMonitor | None" = None,
        mode: ExecutionMode = ExecutionMode.TRAINING,
    ):
        """
        Initialize BotActionInterface.

        Args:
            executor: ActionExecutor implementation (Tkinter/Simulated/Puppeteer)
            state_tracker: StateTracker for state capture and event emission
            confirmation_monitor: Optional ConfirmationMonitor for live mode
            mode: Execution mode (TRAINING, LIVE, etc.)
        """
        self._executor = executor
        self._state_tracker = state_tracker
        self._confirmation_monitor = confirmation_monitor
        self._mode = mode

        # Statistics tracking
        self._total_actions = 0
        self._successful_actions = 0
        self._failed_actions = 0

        logger.info(
            f"BotActionInterface initialized: mode={mode.value}, "
            f"executor={executor.get_mode_name()}, "
            f"confirmation_monitor={'enabled' if confirmation_monitor else 'disabled'}"
        )

    @property
    def mode(self) -> ExecutionMode:
        """Get current execution mode."""
        return self._mode

    @property
    def executor_name(self) -> str:
        """Get executor mode name."""
        return self._executor.get_mode_name()

    def is_available(self) -> bool:
        """
        Check if interface is ready to execute actions.

        Delegates to executor's availability check.

        Returns:
            True if executor is ready, False otherwise
        """
        return self._executor.is_available()

    async def execute(self, params: ActionParams) -> ActionResult:
        """
        Execute action with full lifecycle:

        1. Capture state_before
        2. Capture game_context
        3. Execute via executor
        4. Register with confirmation monitor (if live mode)
        5. Capture state_after (for simulated mode)
        6. Emit player_action event
        7. Return result

        Args:
            params: Action parameters (type, amount, etc.)

        Returns:
            ActionResult with execution outcome and timing info

        Raises:
            Exception: If executor raises during execution
        """
        # Generate action_id
        action_id = str(uuid.uuid4())

        try:
            # Step 1: Capture state before
            logger.debug(f"Action {action_id}: Capturing state_before")
            state_before = self._state_tracker.capture_state_before()

            # Step 2: Capture game context
            logger.debug(f"Action {action_id}: Capturing game_context")
            game_context = self._state_tracker.capture_game_context()

            # Step 3: Execute action via executor
            logger.debug(
                f"Action {action_id}: Executing {params.action_type.value} via {self.executor_name}"
            )
            result = await self._executor.execute(params)

            # Attach action_id if not already set
            if not result.action_id:
                result.action_id = action_id

            # Step 4: Attach captured context
            result.state_before = state_before
            result.game_context = game_context

            # Step 5: Handle confirmation based on mode
            if self._confirmation_monitor and result.success:
                # Live mode: Register with confirmation monitor
                # Confirmation monitor will update state_after when server confirms
                logger.debug(f"Action {action_id}: Registering with ConfirmationMonitor")
                self._confirmation_monitor.register_pending(
                    action_id=result.action_id,
                    action_type=result.action_type,
                    state_before=state_before,
                    callback=None,  # Callback not needed - EventStore listens to EventBus
                )
            else:
                # Simulated/Training mode: Capture state_after immediately
                # (executor has already updated TradeManager state)
                logger.debug(f"Action {action_id}: Capturing state_after (simulated)")
                result.state_after = self._state_tracker.capture_state_before()

            # Step 6: Emit player_action event
            logger.debug(f"Action {action_id}: Emitting PlayerAction event")
            self._state_tracker.emit_player_action(result, params)

            # Step 7: Update statistics
            self._total_actions += 1
            if result.success:
                self._successful_actions += 1
            else:
                self._failed_actions += 1

            logger.info(
                f"Action {action_id} ({params.action_type.value}) "
                f"completed: success={result.success}, "
                f"latency={result.total_latency_ms}ms"
            )

            return result

        except Exception as e:
            # Handle executor exceptions
            self._total_actions += 1
            self._failed_actions += 1

            logger.error(
                f"Action {action_id} ({params.action_type.value}) failed: {e}",
                exc_info=True,
            )

            # Build failure ActionResult
            failure_result = ActionResult(
                success=False,
                action_id=action_id,
                action_type=params.action_type,
                client_ts=int(time.time() * 1000),
                error=str(e),
                state_before=state_before if "state_before" in locals() else None,
                game_context=game_context if "game_context" in locals() else None,
            )

            # Still emit event for failure tracking
            self._state_tracker.emit_player_action(failure_result, params)

            return failure_result

    def get_stats(self) -> dict:
        """
        Get execution statistics.

        Returns:
            dict with execution stats and latency metrics
        """
        stats = {
            "mode": self._mode.value,
            "executor": self.executor_name,
            "total_actions": self._total_actions,
            "successful_actions": self._successful_actions,
            "failed_actions": self._failed_actions,
            "success_rate": (
                self._successful_actions / self._total_actions if self._total_actions > 0 else 0.0
            ),
        }

        # Add latency stats if confirmation monitor is available
        if self._confirmation_monitor:
            latency_stats = self._confirmation_monitor.get_latency_stats()
            stats["latency"] = latency_stats
        else:
            stats["latency"] = {
                "avg_ms": 0.0,
                "min_ms": 0,
                "max_ms": 0,
                "count": 0,
            }

        return stats
