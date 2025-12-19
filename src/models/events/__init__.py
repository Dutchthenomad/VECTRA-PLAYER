"""
Event Models Module - Pydantic schemas for WebSocket events

GitHub Issues: #1-8 (Phase 12A)
Schema Version: 1.0.0
"""

# Issue #1: gameStateUpdate
# Issue #23: gameStatePlayerUpdate (Phase 0 Schema Validation)
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

# Issue #4: playerLeaderboardPosition
from .player_leaderboard_position import (
    LeaderboardPlayerEntry,
    PlayerLeaderboardPosition,
)

# Issue #2: playerUpdate
from .player_update import PlayerUpdate

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
]
