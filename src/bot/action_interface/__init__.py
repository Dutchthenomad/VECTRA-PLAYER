"""
BotActionInterface - Unified action execution layer.

Player Piano Architecture for:
- RECORDING: Track human gameplay with full context
- TRAINING: Fast RL training with simulated execution
- VALIDATION: Animate model decisions on recorded games
- LIVE: Real browser automation (stub in v1.0)
"""

from .confirmation import ConfirmationMonitor, MockConfirmationMonitor
from .executors import ActionExecutor, SimulatedExecutor, TkinterExecutor
from .factory import (
    create_for_live,
    create_for_recording,
    create_for_training,
    create_for_validation,
)
from .interface import BotActionInterface
from .recording import HumanActionInterceptor
from .state import StateTracker
from .types import ActionParams, ActionResult, ActionType, ExecutionMode, GameContext

__all__ = [
    # Main orchestrator
    "BotActionInterface",
    # Types
    "ActionParams",
    "ActionResult",
    "ActionType",
    "ExecutionMode",
    "GameContext",
    # Executors
    "ActionExecutor",
    "SimulatedExecutor",
    "TkinterExecutor",
    # Confirmation
    "ConfirmationMonitor",
    "MockConfirmationMonitor",
    # State
    "StateTracker",
    # Recording
    "HumanActionInterceptor",
    # Factories
    "create_for_training",
    "create_for_recording",
    "create_for_validation",
    "create_for_live",
]
