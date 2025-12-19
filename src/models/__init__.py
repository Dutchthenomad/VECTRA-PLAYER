"""
Data models for Rugs Replay Viewer
"""

from .demo_action import (
    BUTTON_TO_CATEGORY,
    ActionCategory,
    DemoAction,
    StateSnapshot,
    get_category_for_button,
    is_trade_action,
)
from .enums import Phase, PositionStatus, SideBetStatus
from .game_tick import GameTick
from .position import Position

# Recording configuration (JSONL export settings)
from .recording_config import (
    CaptureMode,
    MonitorThresholdType,
    RecordingConfig,
)

# Recording data models (dual-state validation: local vs server)
# Server state from playerUpdate WebSocket event (auth-required, P0)
from .recording_models import (
    DriftDetails,
    GameStateMeta,
    GameStateRecord,
    LocalStateSnapshot,
    PlayerAction,
    PlayerSession,
    PlayerSessionMeta,
    RecordedAction,
    ServerState,
    validate_states,
)
from .side_bet import SideBet

__all__ = [
    "Phase",
    "PositionStatus",
    "SideBetStatus",
    "GameTick",
    "Position",
    "SideBet",
    # Demo action models
    "ActionCategory",
    "BUTTON_TO_CATEGORY",
    "get_category_for_button",
    "is_trade_action",
    "StateSnapshot",
    "DemoAction",
    # Recording data models
    "GameStateMeta",
    "GameStateRecord",
    "PlayerAction",
    "PlayerSessionMeta",
    "PlayerSession",
    # Dual-state validation models (local vs playerUpdate server truth)
    "ServerState",
    "LocalStateSnapshot",
    "DriftDetails",
    "RecordedAction",
    "validate_states",
    # Recording configuration
    "CaptureMode",
    "MonitorThresholdType",
    "RecordingConfig",
]
