"""
Base strategy class for trading bots
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class TradingStrategy(ABC):
    """
    Abstract base class for trading strategies

    Strategies implement the decide() method which returns:
    - action_type: "BUY", "SELL", "SIDE", or "WAIT"
    - amount: Decimal amount (for BUY/SIDE) or None
    - reasoning: String explaining the decision
    """

    def __init__(self):
        """Initialize strategy"""
        self.name = self.__class__.__name__
        self.last_action = None
        self.last_reasoning = None

    @abstractmethod
    def decide(
        self, observation: dict[str, Any], info: dict[str, Any]
    ) -> tuple[str, Decimal | None, str]:
        """
        Make a trading decision based on current game state

        Args:
            observation: Current game state (from bot_get_observation)
            info: Valid actions and constraints (from bot_get_info)

        Returns:
            Tuple of (action_type, amount, reasoning)
            - action_type: "BUY", "SELL", "SIDE", "WAIT"
            - amount: Decimal (for BUY/SIDE) or None (for SELL/WAIT)
            - reasoning: String explaining why this action was chosen
        """
        pass

    def reset(self):
        """Reset strategy state (called on new game)"""
        self.last_action = None
        self.last_reasoning = None

    def __str__(self):
        return self.name

    def _validate_action(
        self, action: str, amount: Decimal | None, reasoning: str, valid_actions: list | None
    ) -> tuple[str, Decimal | None, str]:
        """
        Ensure the chosen action is allowed by the environment.
        Falls back to WAIT if invalid to prevent illegal trades.
        """
        allowed = valid_actions or ["WAIT"]
        normalized = action.upper()

        if normalized not in allowed:
            logger.warning(
                f"Desired action {normalized} not in allowed actions {allowed}, defaulting to WAIT"
            )
            return ("WAIT", None, "Action not permitted; waiting")

        return (normalized, amount, reasoning)
