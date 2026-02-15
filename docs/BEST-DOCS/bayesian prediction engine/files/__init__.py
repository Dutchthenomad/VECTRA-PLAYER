"""
Bayesian Predictor for rugs.fun

A real-time prediction system based on mean-reversion analysis.
"""

from .game_state_manager import CompletedGame, GamePhase, GameStateManager
from .prediction_engine import LivePrediction, LivePredictionEngine

__version__ = "0.1.0"
__all__ = [
    "GameStateManager",
    "CompletedGame",
    "GamePhase",
    "LivePredictionEngine",
    "LivePrediction",
]
