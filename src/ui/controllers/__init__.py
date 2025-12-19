"""
UI Controllers Package

Contains controller classes extracted from MainWindow to follow Single Responsibility Principle.
Each controller handles a specific aspect of the application.
"""

from .bot_manager import BotManager
from .browser_bridge_controller import BrowserBridgeController
from .live_feed_controller import LiveFeedController

# Recording controller (JSONL export, dual-state validation)
from .recording_controller import RecordingController
from .replay_controller import ReplayController
from .trading_controller import TradingController

__all__ = [
    "BotManager",
    "BrowserBridgeController",
    "LiveFeedController",
    "RecordingController",
    "ReplayController",
    "TradingController",
]
