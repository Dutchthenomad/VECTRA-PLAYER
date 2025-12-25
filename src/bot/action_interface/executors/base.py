"""
ActionExecutor abstract base class.

Defines the interface for all action execution strategies.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import ActionParams, ActionResult


class ActionExecutor(ABC):
    """
    Abstract base for action execution strategies.

    Implementations:
    - TkinterExecutor: Wraps BotUIController for Tkinter button clicks
    - SimulatedExecutor: Fast execution via TradeManager for training
    - PuppeteerExecutor: Browser automation via CDP
    """

    @abstractmethod
    async def execute(self, params: "ActionParams") -> "ActionResult":
        """
        Execute an action.

        Args:
            params: Action parameters (type, amount, etc.)

        Returns:
            ActionResult with success/failure and timing info
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this executor is ready to execute actions."""
        pass

    @abstractmethod
    def get_mode_name(self) -> str:
        """Return human-readable mode name."""
        pass
