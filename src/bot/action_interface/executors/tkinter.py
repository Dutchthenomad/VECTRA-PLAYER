"""
TkinterExecutor - UI-layer execution using BotUIController.

Wraps existing BotUIController to provide ActionExecutor interface.
Includes optional button animation for visual feedback.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING

from ..types import ActionParams, ActionResult
from .base import ActionExecutor

if TYPE_CHECKING:
    from bot.ui_controller import BotUIController

from models.events.player_action import ActionType

logger = logging.getLogger(__name__)


class TkinterExecutor(ActionExecutor):
    """
    Execute actions via Tkinter UI using BotUIController.

    Wraps BotUIController to provide ActionExecutor interface.
    Supports optional button animation for visual feedback.
    """

    def __init__(
        self,
        ui_controller: BotUIController,
        animate: bool = True,
    ):
        """
        Initialize TkinterExecutor.

        Args:
            ui_controller: BotUIController instance for UI interaction
            animate: Enable button animation (default True)
        """
        self._ui_controller = ui_controller
        self._animate = animate

    def is_available(self) -> bool:
        """Check if UI controller is ready."""
        return self._ui_controller is not None

    def get_mode_name(self) -> str:
        """Return mode name."""
        return "tkinter"

    async def execute(self, params: ActionParams) -> ActionResult:
        """
        Execute action via BotUIController.

        Routes to appropriate UI controller method based on action type:
        - BUY: execute_buy_with_amount()
        - SELL: click_sell() + set_sell_percentage()
        - SIDEBET: execute_sidebet_with_amount()
        - BET_INCREMENT: click_increment_button()
        - Others: No-op (return success)

        Args:
            params: Action parameters

        Returns:
            ActionResult with execution outcome
        """
        action_id = str(uuid.uuid4())
        client_ts = int(time.time() * 1000)

        try:
            success = False

            # Route to appropriate UI controller method
            if params.action_type == ActionType.BUY:
                if params.amount is None:
                    raise ValueError("BUY action requires amount parameter")
                success = self._ui_controller.execute_buy_with_amount(params.amount)

            elif params.action_type == ActionType.SELL:
                # Convert percentage to float if provided
                percentage = float(params.percentage) if params.percentage else None
                success = self._ui_controller.click_sell(percentage=percentage)

            elif params.action_type == ActionType.SIDEBET:
                if params.amount is None:
                    raise ValueError("SIDEBET action requires amount parameter")
                success = self._ui_controller.execute_sidebet_with_amount(params.amount)

            elif params.action_type == ActionType.BET_INCREMENT:
                if params.button is None:
                    raise ValueError("BET_INCREMENT requires button parameter")
                success = self._ui_controller.click_increment_button(params.button)

            elif params.action_type == ActionType.BET_DECREMENT:
                # Decrement is treated as increment with appropriate button
                # (assuming button param specifies the decrement button)
                if params.button is None:
                    raise ValueError("BET_DECREMENT requires button parameter")
                success = self._ui_controller.click_increment_button(params.button)

            elif params.action_type == ActionType.BET_PERCENTAGE:
                # Percentage button (e.g., "1/2", "X2", "MAX")
                if params.button is None:
                    raise ValueError("BET_PERCENTAGE requires button parameter")
                success = self._ui_controller.click_increment_button(params.button)

            else:
                # Unknown action type - treat as no-op
                logger.warning(f"Unsupported action type: {params.action_type}")
                success = True

            # UI controller methods don't return execution details,
            # so we can't populate executed_price/executed_amount
            return ActionResult(
                success=success,
                action_id=action_id,
                action_type=params.action_type,
                client_ts=client_ts,
                executed_amount=params.amount if success else None,
            )

        except Exception as e:
            logger.error(f"TkinterExecutor error: {e}")
            return ActionResult(
                success=False,
                action_id=action_id,
                action_type=params.action_type,
                client_ts=client_ts,
                error=str(e),
            )
