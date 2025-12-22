"""
Trading strategies for bot automation

DEPRECATED: These strategies are reference implementations from an early prototype.
They will be replaced when the ML/RL bot system is rebuilt from scratch.

Kept for:
- Informing ML/RL development planning
- Reference for entry/exit logic patterns
- Empirical parameters (sweet spots, temporal windows, etc.)

Do NOT invest time refactoring these - they're being replaced.
"""

from .aggressive import AggressiveStrategy
from .base import TradingStrategy
from .conservative import ConservativeStrategy
from .foundational import FoundationalStrategy
from .sidebet import SidebetStrategy

# Strategy registry
STRATEGIES = {
    "conservative": ConservativeStrategy,
    "aggressive": AggressiveStrategy,
    "sidebet": SidebetStrategy,
    "foundational": FoundationalStrategy,  # Evidence-based strategy from empirical analysis
}


def get_strategy(name: str) -> TradingStrategy:
    """
    Get strategy instance by name

    Args:
        name: Strategy name (conservative, aggressive, sidebet)

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy name is invalid
    """
    name = name.lower()
    if name not in STRATEGIES:
        valid_strategies = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Invalid strategy '{name}'. Valid strategies: {valid_strategies}")

    return STRATEGIES[name]()


def list_strategies() -> list:
    """List available strategy names"""
    return list(STRATEGIES.keys())


__all__ = [
    "AggressiveStrategy",
    "ConservativeStrategy",
    "FoundationalStrategy",
    "SidebetStrategy",
    "TradingStrategy",
    "get_strategy",
    "list_strategies",
]
