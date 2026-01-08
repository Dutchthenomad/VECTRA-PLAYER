"""
UI Controllers Package - Minimal Version

Only essential controllers for RL training data collection.
Archived controllers: BotManager, LiveFeedController, ReplayController
"""

from .browser_bridge_controller import BrowserBridgeController
from .recording_controller import RecordingController
from .trading_controller import TradingController

__all__ = [
    "BrowserBridgeController",
    "RecordingController",
    "TradingController",
]
