"""
Event Models Module - Pydantic schemas for WebSocket events

GitHub Issues: #1-8 (Phase 12A)
Schema Version: 1.0.0
"""

# Issue #1: gameStateUpdate
from .game_state_update import (
    GameStateUpdate,
    LeaderboardEntry,
    PartialPrices,
    GameHistoryEntry,
    ProvablyFair,
    RugRoyale,
    AvailableShitcoin,
    Rugpool,
    SideBet,
    ShortPosition,
)

# Issue #2: playerUpdate
from .player_update import PlayerUpdate

# Issue #3: usernameStatus
from .username_status import UsernameStatus

# Issue #4: playerLeaderboardPosition
from .player_leaderboard_position import (
    PlayerLeaderboardPosition,
    LeaderboardPlayerEntry,
)

# Issues #5, #6, #7: Trade events
from .trade_events import (
    NewTrade,
    SidebetRequest,
    SidebetResponse,
    BuyOrderRequest,
    SellOrderRequest,
    TradeOrderResponse,
)

# Issue #8: System events
from .system_events import (
    SystemEventType,
    SystemEvent,
    ConnectionEvent,
    AuthEvent,
    GameLifecycleEvent,
    SessionEvent,
)

__all__ = [
    # Issue #1: gameStateUpdate
    'GameStateUpdate',
    'LeaderboardEntry',
    'PartialPrices',
    'GameHistoryEntry',
    'ProvablyFair',
    'RugRoyale',
    'AvailableShitcoin',
    'Rugpool',
    'SideBet',
    'ShortPosition',
    # Issue #2: playerUpdate
    'PlayerUpdate',
    # Issue #3: usernameStatus
    'UsernameStatus',
    # Issue #4: playerLeaderboardPosition
    'PlayerLeaderboardPosition',
    'LeaderboardPlayerEntry',
    # Issue #5: standard/newTrade
    'NewTrade',
    # Issue #6: sidebetResponse
    'SidebetRequest',
    'SidebetResponse',
    # Issue #7: buyOrder/sellOrder
    'BuyOrderRequest',
    'SellOrderRequest',
    'TradeOrderResponse',
    # Issue #8: System events
    'SystemEventType',
    'SystemEvent',
    'ConnectionEvent',
    'AuthEvent',
    'GameLifecycleEvent',
    'SessionEvent',
]
