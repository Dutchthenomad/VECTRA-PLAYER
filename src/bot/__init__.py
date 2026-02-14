"""Bot module - Trading strategies and bot controller"""

from .bet_amount_sequencer import calculate_optimal_sequence, estimate_clicks
from .controller import BotController
from .execution_bridge import BotExecutionBridge
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
    "BotExecutionBridge",
    "BotInterface",
    "ConservativeStrategy",
    "SidebetStrategy",
    "TradingStrategy",
    "calculate_optimal_sequence",
    "estimate_clicks",
    "get_strategy",
    "list_strategies",
]
