"""
Human click interception for recording mode.

Wraps UI button callbacks to capture actions via BotActionInterface.
When a human clicks BUY/SELL/SIDEBET, the action is recorded with full context.
"""

import asyncio
import logging
from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..interface import BotActionInterface

from models.events.player_action import ActionType

from ..types import ActionParams

logger = logging.getLogger(__name__)


class HumanActionInterceptor:
    """
    Intercepts human button clicks for recording.

    Usage:
        interceptor = HumanActionInterceptor(action_interface)

        # Wrap button callbacks in main_window setup
        buy_button.config(command=interceptor.wrap_buy(original_buy_handler, get_amount))
        sell_button.config(command=interceptor.wrap_sell(original_sell_handler, get_percentage))
        sidebet_button.config(command=interceptor.wrap_sidebet(original_sidebet_handler, get_amount))
    """

    def __init__(self, action_interface: "BotActionInterface"):
        """
        Initialize interceptor.

        Args:
            action_interface: BotActionInterface configured for RECORDING mode
        """
        self._interface = action_interface
        self._loop = None  # Will be set lazily for async execution
        logger.info("HumanActionInterceptor initialized")

    def _get_event_loop(self):
        """Get or create event loop for async execution."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def _schedule_recording(self, params: ActionParams) -> None:
        """Schedule async recording without blocking UI."""
        try:
            loop = self._get_event_loop()
            # Create task for async execution (fire-and-forget pattern)
            # We don't need to track the task - recording failures are logged but not critical
            asyncio.ensure_future(self._record_action(params), loop=loop)  # noqa: RUF006
        except Exception as e:
            logger.error(f"Failed to schedule recording: {e}")

    async def _record_action(self, params: ActionParams) -> None:
        """Record action via BotActionInterface."""
        try:
            result = await self._interface.execute(params)
            logger.debug(
                f"Recorded human action: {params.action_type.value} "
                f"success={result.success} latency={result.total_latency_ms}ms"
            )
        except Exception as e:
            logger.error(f"Failed to record action: {e}")

    def wrap_buy(
        self,
        original_handler: Callable[[], None],
        get_amount: Callable[[], Decimal],
    ) -> Callable[[], None]:
        """
        Wrap BUY button handler.

        Args:
            original_handler: Original button callback
            get_amount: Function that returns current bet amount

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            # Get amount before executing (UI may change)
            amount = get_amount()

            # Record the action
            params = ActionParams(action_type=ActionType.BUY, amount=amount)
            self._schedule_recording(params)

            # Call original handler
            original_handler()

        return wrapped

    def wrap_sell(
        self,
        original_handler: Callable[[], None],
        get_percentage: Callable[[], Decimal],
    ) -> Callable[[], None]:
        """
        Wrap SELL button handler.

        Args:
            original_handler: Original button callback
            get_percentage: Function that returns current sell percentage

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            percentage = get_percentage()

            params = ActionParams(action_type=ActionType.SELL, percentage=percentage)
            self._schedule_recording(params)

            original_handler()

        return wrapped

    def wrap_sidebet(
        self,
        original_handler: Callable[[], None],
        get_amount: Callable[[], Decimal],
    ) -> Callable[[], None]:
        """
        Wrap SIDEBET button handler.

        Args:
            original_handler: Original button callback
            get_amount: Function that returns current bet amount

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            amount = get_amount()

            params = ActionParams(action_type=ActionType.SIDEBET, amount=amount)
            self._schedule_recording(params)

            original_handler()

        return wrapped

    def wrap_increment(
        self,
        original_handler: Callable[[], None],
        button_text: str,
    ) -> Callable[[], None]:
        """
        Wrap increment button handler (+0.001, +0.01, etc.).

        Args:
            original_handler: Original button callback
            button_text: Button identifier (e.g., "+0.01", "X", "1/2")

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            params = ActionParams(
                action_type=ActionType.BET_INCREMENT,
                button=button_text,
            )
            self._schedule_recording(params)

            original_handler()

        return wrapped

    def wrap_percentage(
        self,
        original_handler: Callable[[], None],
        percentage: Decimal,
    ) -> Callable[[], None]:
        """
        Wrap percentage button handler (10%, 25%, 50%, 100%).

        Args:
            original_handler: Original button callback
            percentage: Percentage value (e.g., Decimal("0.25"))

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            params = ActionParams(
                action_type=ActionType.BET_PERCENTAGE,
                percentage=percentage,
            )
            self._schedule_recording(params)

            original_handler()

        return wrapped
