"""UI handlers module."""

from ui.handlers.balance_handlers import BalanceHandlersMixin
from ui.handlers.capture_handlers import CaptureHandlersMixin
from ui.handlers.event_handlers import EventHandlersMixin
from ui.handlers.player_handlers import PlayerHandlersMixin
from ui.handlers.recording_handlers import RecordingHandlersMixin
from ui.handlers.replay_handlers import ReplayHandlersMixin

__all__ = [
    "BalanceHandlersMixin",
    "CaptureHandlersMixin",
    "EventHandlersMixin",
    "PlayerHandlersMixin",
    "RecordingHandlersMixin",
    "ReplayHandlersMixin",
]
