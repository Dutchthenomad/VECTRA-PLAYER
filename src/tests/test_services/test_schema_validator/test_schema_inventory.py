"""
Tests for Schema Validator Registry - Issue #23

Tests the schema registry mapping and coverage statistics.
"""

from pydantic import BaseModel

from models.events import (
    GameStatePlayerUpdate,
    GameStateUpdate,
    NewTrade,
    PlayerUpdate,
    SidebetResponse,
    TradeOrderResponse,
)
from services.schema_validator.registry import (
    IN_SCOPE_EVENTS,
    OUT_OF_SCOPE_EVENTS,
    SCHEMA_REGISTRY,
    get_coverage_stats,
    get_in_scope_events,
    get_schema_for_event,
    is_out_of_scope,
)


class TestSchemaRegistry:
    """Test the schema registry mapping."""

    def test_registry_has_all_in_scope_events(self):
        """All in-scope events should have a registered schema."""
        for event in IN_SCOPE_EVENTS:
            assert event in SCHEMA_REGISTRY, f"Missing schema for in-scope event: {event}"

    def test_registry_maps_to_pydantic_models(self):
        """All registry values should be Pydantic BaseModel subclasses."""
        for event, schema in SCHEMA_REGISTRY.items():
            assert issubclass(schema, BaseModel), (
                f"{event} schema is not a Pydantic model: {schema}"
            )

    def test_game_state_update_registered(self):
        """gameStateUpdate should map to GameStateUpdate."""
        assert SCHEMA_REGISTRY["gameStateUpdate"] is GameStateUpdate

    def test_game_state_player_update_registered(self):
        """gameStatePlayerUpdate should map to GameStatePlayerUpdate."""
        assert SCHEMA_REGISTRY["gameStatePlayerUpdate"] is GameStatePlayerUpdate

    def test_player_update_registered(self):
        """playerUpdate should map to PlayerUpdate."""
        assert SCHEMA_REGISTRY["playerUpdate"] is PlayerUpdate

    def test_trade_events_registered(self):
        """Trade events should be registered."""
        assert SCHEMA_REGISTRY["standard/newTrade"] is NewTrade
        assert SCHEMA_REGISTRY["newTrade"] is NewTrade
        assert SCHEMA_REGISTRY["sidebetResponse"] is SidebetResponse
        assert SCHEMA_REGISTRY["buyOrderResponse"] is TradeOrderResponse
        assert SCHEMA_REGISTRY["sellOrderResponse"] is TradeOrderResponse


class TestGetSchemaForEvent:
    """Test the get_schema_for_event function."""

    def test_returns_schema_for_known_event(self):
        """Should return schema for registered event."""
        schema = get_schema_for_event("gameStateUpdate")
        assert schema is GameStateUpdate

    def test_returns_none_for_unknown_event(self):
        """Should return None for unregistered event."""
        schema = get_schema_for_event("nonexistent_event")
        assert schema is None

    def test_returns_none_for_out_of_scope_event(self):
        """Out-of-scope events should not be in registry."""
        schema = get_schema_for_event("newChatMessage")
        assert schema is None


class TestOutOfScopeEvents:
    """Test out-of-scope event handling."""

    def test_out_of_scope_events_defined(self):
        """Should have out-of-scope events defined."""
        assert "newChatMessage" in OUT_OF_SCOPE_EVENTS
        assert "goldenHourUpdate" in OUT_OF_SCOPE_EVENTS
        assert "goldenHourDrawing" in OUT_OF_SCOPE_EVENTS
        assert "battleEventUpdate" in OUT_OF_SCOPE_EVENTS

    def test_is_out_of_scope_returns_true(self):
        """is_out_of_scope should return True for out-of-scope events."""
        assert is_out_of_scope("newChatMessage") is True
        assert is_out_of_scope("goldenHourUpdate") is True

    def test_is_out_of_scope_returns_false(self):
        """is_out_of_scope should return False for in-scope events."""
        assert is_out_of_scope("gameStateUpdate") is False
        assert is_out_of_scope("playerUpdate") is False


class TestCoverageStats:
    """Test the coverage statistics."""

    def test_coverage_stats_structure(self):
        """Coverage stats should have expected fields."""
        stats = get_coverage_stats()
        assert "total_in_scope" in stats
        assert "covered" in stats
        assert "missing" in stats
        assert "coverage_pct" in stats
        assert "covered_events" in stats
        assert "missing_events" in stats

    def test_full_coverage(self):
        """Should report 100% coverage when all in-scope events have schemas."""
        stats = get_coverage_stats()
        assert stats["coverage_pct"] == 100.0
        assert stats["missing"] == 0
        assert len(stats["missing_events"]) == 0

    def test_covered_events_are_sorted(self):
        """Covered events should be sorted alphabetically."""
        stats = get_coverage_stats()
        assert stats["covered_events"] == sorted(stats["covered_events"])


class TestGetInScopeEvents:
    """Test the get_in_scope_events function."""

    def test_returns_copy(self):
        """Should return a copy, not the original set."""
        events = get_in_scope_events()
        events.add("test_event")
        assert "test_event" not in IN_SCOPE_EVENTS

    def test_contains_expected_events(self):
        """Should contain all expected in-scope events."""
        events = get_in_scope_events()
        assert "gameStateUpdate" in events
        assert "gameStatePlayerUpdate" in events
        assert "playerUpdate" in events
        assert "usernameStatus" in events
        assert "playerLeaderboardPosition" in events
        assert "connect" in events
        assert "disconnect" in events
