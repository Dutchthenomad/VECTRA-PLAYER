"""
Event Models Module - Pydantic schemas for WebSocket events

GitHub Issues: #1-8 (Phase 12A)
Schema Version: 1.0.0
"""

# Issue #1: gameStateUpdate
# Issue #23: gameStatePlayerUpdate (Phase 0 Schema Validation)
from .alert_trigger import AlertTrigger, AlertType
from .bbc_round import BBCPrediction, BBCRound
from .candleflip import CandleflipChoice, CandleflipRound
from .game_state_update import (
    AvailableShitcoin,
    GameHistoryEntry,
    GameStatePlayerUpdate,
    GameStateUpdate,
    LeaderboardEntry,
    PartialPrices,
    ProvablyFair,
    Rugpool,
    RugRoyale,
    ShortPosition,
    SideBet,
)
from .ml_episode import MLEpisode
from .other_player import ExceptionalPlayer, OtherActionType, OtherPlayerAction

# Issue #2: playerUpdate
from .player_action import (
    ActionOutcome,
    ActionTimestamps,
    ActionType,
    GameContext,
    GamePhase,
    PlayerAction,
    PlayerState,
)

# Issue #4: playerLeaderboardPosition
from .player_leaderboard_position import (
    LeaderboardPlayerEntry,
    PlayerLeaderboardPosition,
)
from .player_update import PlayerUpdate
from .short_position import ShortPositionState

# Issue #8: System events
from .system_events import (
    AuthEvent,
    ConnectionEvent,
    GameLifecycleEvent,
    SessionEvent,
    SystemEvent,
    SystemEventType,
)

# Issues #5, #6, #7: Trade events
from .trade_events import (
    BuyOrderRequest,
    NewTrade,
    SellOrderRequest,
    SidebetRequest,
    SidebetResponse,
    TradeOrderResponse,
)

# Issue #3: usernameStatus
from .username_status import UsernameStatus

__all__ = [
    # Issue #1: gameStateUpdate
    "GameStateUpdate",
    # Issue #23: gameStatePlayerUpdate
    "GameStatePlayerUpdate",
    "LeaderboardEntry",
    "PartialPrices",
    "GameHistoryEntry",
    "ProvablyFair",
    "RugRoyale",
    "AvailableShitcoin",
    "Rugpool",
    "SideBet",
    "ShortPosition",
    # Issue #136: player actions
    "ActionType",
    "GamePhase",
    "GameContext",
    "PlayerState",
    "ActionTimestamps",
    "ActionOutcome",
    "PlayerAction",
    # Issue #136: other player events
    "OtherActionType",
    "OtherPlayerAction",
    "ExceptionalPlayer",
    # Issue #2: playerUpdate
    "PlayerUpdate",
    # Issue #3: usernameStatus
    "UsernameStatus",
    # Issue #4: playerLeaderboardPosition
    "PlayerLeaderboardPosition",
    "LeaderboardPlayerEntry",
    # Issue #5: standard/newTrade
    "NewTrade",
    # Issue #6: sidebetResponse
    "SidebetRequest",
    "SidebetResponse",
    # Issue #7: buyOrder/sellOrder
    "BuyOrderRequest",
    "SellOrderRequest",
    "TradeOrderResponse",
    # Issue #8: System events
    "SystemEventType",
    "SystemEvent",
    "ConnectionEvent",
    "AuthEvent",
    "GameLifecycleEvent",
    "SessionEvent",
    # Issue #136: alert triggers
    "AlertType",
    "AlertTrigger",
    # Issue #136: ML episodes
    "MLEpisode",
    # Issue #136: sidegames placeholders
    "BBCPrediction",
    "BBCRound",
    "CandleflipChoice",
    "CandleflipRound",
    "ShortPositionState",
]
