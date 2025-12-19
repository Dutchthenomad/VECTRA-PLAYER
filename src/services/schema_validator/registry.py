"""
Schema Registry - Maps Socket.IO event names to Pydantic schemas

GitHub Issue: #23
Schema Version: 1.0.0

IN-SCOPE Events (11 total):
- gameStateUpdate
- gameStatePlayerUpdate
- playerUpdate
- usernameStatus
- playerLeaderboardPosition
- standard/newTrade
- sidebetResponse
- buyOrderResponse / sellOrderResponse (mapped to TradeOrderResponse)
- connect
- disconnect

OUT-OF-SCOPE Events (silently skipped):
- newChatMessage
- goldenHourUpdate
- goldenHourDrawing
- battleEventUpdate
"""

from pydantic import BaseModel

from models.events import (
    GameStatePlayerUpdate,
    GameStateUpdate,
    NewTrade,
    PlayerLeaderboardPosition,
    PlayerUpdate,
    SidebetResponse,
    TradeOrderResponse,
    UsernameStatus,
)
from models.events.system_events import ConnectionEvent

# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    # Issue #1: Primary game state
    "gameStateUpdate": GameStateUpdate,
    # Issue #23: Player-specific rugpool
    "gameStatePlayerUpdate": GameStatePlayerUpdate,
    # Issue #2: Player state
    "playerUpdate": PlayerUpdate,
    # Issue #3: Username
    "usernameStatus": UsernameStatus,
    # Issue #4: Leaderboard position
    "playerLeaderboardPosition": PlayerLeaderboardPosition,
    # Issue #5: Trade notifications
    "standard/newTrade": NewTrade,
    "newTrade": NewTrade,  # Alternative name
    # Issue #6: Sidebet
    "sidebetResponse": SidebetResponse,
    # Issue #7: Trade orders
    "buyOrderResponse": TradeOrderResponse,
    "sellOrderResponse": TradeOrderResponse,
    # Issue #8: System events
    "connect": ConnectionEvent,
    "disconnect": ConnectionEvent,
}

# Events that should be in scope for validation (from Issue #23)
IN_SCOPE_EVENTS = {
    "gameStateUpdate",
    "gameStatePlayerUpdate",
    "playerUpdate",
    "usernameStatus",
    "playerLeaderboardPosition",
    "standard/newTrade",
    "newTrade",
    "sidebetResponse",
    "buyOrderResponse",
    "sellOrderResponse",
    "connect",
    "disconnect",
}

# Events explicitly out of scope (silently skipped)
OUT_OF_SCOPE_EVENTS = {
    "newChatMessage",
    "goldenHourUpdate",
    "goldenHourDrawing",
    "battleEventUpdate",
}


def get_schema_for_event(event_name: str) -> type[BaseModel] | None:
    """
    Get the Pydantic schema for a given event name.

    Args:
        event_name: Socket.IO event name

    Returns:
        Pydantic BaseModel class or None if not registered
    """
    return SCHEMA_REGISTRY.get(event_name)


def get_in_scope_events() -> set[str]:
    """Get the set of event names that are in scope for validation."""
    return IN_SCOPE_EVENTS.copy()


def is_out_of_scope(event_name: str) -> bool:
    """Check if an event is explicitly out of scope."""
    return event_name in OUT_OF_SCOPE_EVENTS


def get_coverage_stats() -> dict:
    """
    Get schema coverage statistics.

    Returns:
        Dict with coverage metrics
    """
    in_scope = IN_SCOPE_EVENTS
    registered = set(SCHEMA_REGISTRY.keys())
    covered = in_scope & registered
    missing = in_scope - registered

    return {
        "total_in_scope": len(in_scope),
        "covered": len(covered),
        "missing": len(missing),
        "coverage_pct": len(covered) / len(in_scope) * 100 if in_scope else 0,
        "covered_events": sorted(covered),
        "missing_events": sorted(missing),
    }
