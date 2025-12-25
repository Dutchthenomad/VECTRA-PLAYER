"""
SimulatedExecutor - Fast simulated execution for RL training.

No actual UI interaction - uses TradeManager directly.
Perfect for RL training loops requiring 1000s of iterations.
"""

from __future__ import annotations

import logging
import time
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from ..types import ActionParams, ActionResult
from .base import ActionExecutor

if TYPE_CHECKING:
    from core.game_state import GameState
    from core.trade_manager import TradeManager

from models.events.player_action import ActionType

logger = logging.getLogger(__name__)


class SimulatedExecutor(ActionExecutor):
    """
    Execute actions via direct TradeManager calls.

    Fastest execution path - no UI delays.
    Used for TRAINING mode in RL pipelines.
    """

    def __init__(
        self,
        game_state: GameState,
        trade_manager: TradeManager,
        simulated_latency_ms: int = 0,
    ):
        """
        Initialize SimulatedExecutor.

        Args:
            game_state: GameState instance for state access
            trade_manager: TradeManager for trade execution
            simulated_latency_ms: Simulated network latency (default 0 for training)
        """
        self._game_state = game_state
        self._trade_manager = trade_manager
        self._simulated_latency_ms = simulated_latency_ms

    def is_available(self) -> bool:
        """Simulated executor is always available."""
        return True

    def get_mode_name(self) -> str:
        """Return mode name."""
        return "simulated"

    async def execute(self, params: ActionParams) -> ActionResult:
        """
        Execute action via TradeManager (instant).

        Args:
            params: Action parameters

        Returns:
            ActionResult with execution outcome
        """
        action_id = str(uuid.uuid4())
        client_ts = int(time.time() * 1000)

        try:
            result_dict: dict[str, Any] = {}

            # Handle different action types
            if params.action_type == ActionType.BUY:
                result_dict = self._trade_manager.execute_buy(params.amount)

            elif params.action_type == ActionType.SELL:
                # Set percentage first if provided and not 100%
                if params.percentage and params.percentage != Decimal("1.0"):
                    self._game_state.set_sell_percentage(params.percentage)
                result_dict = self._trade_manager.execute_sell()

            elif params.action_type == ActionType.SIDEBET:
                result_dict = self._trade_manager.execute_sidebet(params.amount)

            elif params.action_type == ActionType.BET_INCREMENT:
                # Bet increment doesn't execute trades, just a no-op
                result_dict = {"success": True, "action": "BET_INCREMENT"}

            elif params.action_type == ActionType.BET_DECREMENT:
                # Bet decrement doesn't execute trades, just a no-op
                result_dict = {"success": True, "action": "BET_DECREMENT"}

            elif params.action_type == ActionType.BET_PERCENTAGE:
                # Percentage button doesn't execute trades
                result_dict = {"success": True, "action": "BET_PERCENTAGE"}

            else:
                result_dict = {
                    "success": False,
                    "reason": f"Unsupported action type: {params.action_type}",
                }

            success = result_dict.get("success", False)
            error = result_dict.get("reason") if not success else None

            # Extract executed price/amount from result
            executed_price = None
            executed_amount = None
            if "price" in result_dict:
                executed_price = Decimal(str(result_dict["price"]))
            if "amount" in result_dict:
                executed_amount = Decimal(str(result_dict["amount"]))

            # Calculate simulated timestamps
            server_ts = client_ts + self._simulated_latency_ms // 2
            confirmed_ts = client_ts + self._simulated_latency_ms

            return ActionResult(
                success=success,
                action_id=action_id,
                action_type=params.action_type,
                client_ts=client_ts,
                server_ts=server_ts,
                confirmed_ts=confirmed_ts,
                executed_price=executed_price,
                executed_amount=executed_amount,
                error=error,
            )

        except Exception as e:
            logger.error(f"SimulatedExecutor error: {e}")
            return ActionResult(
                success=False,
                action_id=action_id,
                action_type=params.action_type,
                client_ts=client_ts,
                error=str(e),
            )
