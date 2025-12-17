"""
Sidebet prediction module for Rugs.fun RL bot

This module implements the sidebet prediction system that identifies
optimal timing for placing sidebets (rug predictions) using a 14-feature
machine learning model.

Key components:
- FeatureExtractor: Extracts 14 strategic features
- GameDataProcessor: Processes JSONL game files
- SidebetModel: Gradient Boosting classifier
- SidebetPredictor: Real-time prediction wrapper for RL integration
- SidebetBacktester: Martingale sequence backtesting
"""

from .data_processor import GameDataProcessor, RollingStats
from .feature_extractor import FEATURE_NAMES, FeatureExtractor
from .model import SidebetModel
from .predictor import SidebetPredictor

__all__ = [
    "FEATURE_NAMES",
    "FeatureExtractor",
    "GameDataProcessor",
    "RollingStats",
    "SidebetModel",
    "SidebetPredictor",
]
