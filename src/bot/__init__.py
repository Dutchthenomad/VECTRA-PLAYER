"""Bot module - Trading strategies and bot controller"""

from .controller import BotController
from .interface import BotInterface
from .strategies import (
    AggressiveStrategy,
    ConservativeStrategy,
    SidebetStrategy,
    TradingStrategy,
    get_strategy,
    list_strategies,
)

__all__ = [
    "AggressiveStrategy",
    "BotController",
    "BotInterface",
    "ConservativeStrategy",
    "SidebetStrategy",
    "TradingStrategy",
    "get_strategy",
    "list_strategies",
]
