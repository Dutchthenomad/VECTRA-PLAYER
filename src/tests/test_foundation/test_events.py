"""
Tests for Foundation Event Types - Typed dataclasses for all event types.

TDD: Tests written BEFORE implementation.
"""


# =============================================================================
# PHASE 1: GameTickEvent Tests
# =============================================================================


class TestGameTickEvent:
    """Test GameTickEvent dataclass."""

    def test_create_game_tick_event_from_dict(self):
        """Create GameTickEvent from Foundation normalized dict."""
        from foundation.events import GameTickEvent

        data = {
            "type": "game.tick",
            "ts": 1737200000000,
            "gameId": "20260118-abc123",
            "seq": 42,
            "data": {
                "active": True,
                "rugged": False,
                "price": 1.523,
                "tickCount": 15,
                "cooldownTimer": 0,
                "allowPreRoundBuys": False,
                "tradeCount": 8,
                "phase": "ACTIVE",
                "gameHistory": None,
                "leaderboard": [],
            },
        }

        event = GameTickEvent.from_dict(data)

        assert event.type == "game.tick"
        assert event.ts == 1737200000000
        assert event.game_id == "20260118-abc123"
        assert event.seq == 42
        assert event.active is True
        assert event.rugged is False
        assert event.price == 1.523
        assert event.tick_count == 15
        assert event.phase == "ACTIVE"

    def test_game_tick_event_default_values(self):
        """GameTickEvent has sensible defaults."""
        from foundation.events import GameTickEvent

        event = GameTickEvent(
            type="game.tick",
            ts=1737200000000,
            game_id="test",
            seq=1,
        )

        assert event.active is False
        assert event.rugged is False
        assert event.price == 1.0
        assert event.tick_count == 0
        assert event.phase == "UNKNOWN"
        assert event.leaderboard == []

    def test_game_tick_event_to_dict(self):
        """GameTickEvent.to_dict() returns serializable dict."""
        from foundation.events import GameTickEvent

        event = GameTickEvent(
            type="game.tick",
            ts=1737200000000,
            game_id="test",
            seq=1,
            active=True,
            price=2.0,
            phase="ACTIVE",
        )

        result = event.to_dict()

        assert result["type"] == "game.tick"
        assert result["ts"] == 1737200000000
        assert result["gameId"] == "test"
        assert result["active"] is True
        assert result["price"] == 2.0


# =============================================================================
# PHASE 2: PlayerStateEvent Tests
# =============================================================================


class TestPlayerStateEvent:
    """Test PlayerStateEvent dataclass."""

    def test_create_player_state_event_from_dict(self):
        """Create PlayerStateEvent from Foundation normalized dict."""
        from foundation.events import PlayerStateEvent

        data = {
            "type": "player.state",
            "ts": 1737200000000,
            "gameId": "20260118-abc123",
            "seq": 50,
            "data": {
                "cash": 3.967,
                "positionQty": 0.222,
                "avgCost": 1.259,
                "cumulativePnL": 0.264,
                "totalInvested": 0.28,
            },
        }

        event = PlayerStateEvent.from_dict(data)

        assert event.type == "player.state"
        assert event.ts == 1737200000000
        assert event.game_id == "20260118-abc123"
        assert event.seq == 50
        assert event.cash == 3.967
        assert event.position_qty == 0.222
        assert event.avg_cost == 1.259
        assert event.cumulative_pnl == 0.264
        assert event.total_invested == 0.28

    def test_player_state_event_default_values(self):
        """PlayerStateEvent has sensible defaults."""
        from foundation.events import PlayerStateEvent

        event = PlayerStateEvent(
            type="player.state",
            ts=1737200000000,
            game_id="test",
            seq=1,
        )

        assert event.cash == 0.0
        assert event.position_qty == 0.0
        assert event.avg_cost == 0.0
        assert event.cumulative_pnl == 0.0
        assert event.total_invested == 0.0


# =============================================================================
# PHASE 3: ConnectionAuthenticatedEvent Tests
# =============================================================================


class TestConnectionAuthenticatedEvent:
    """Test ConnectionAuthenticatedEvent dataclass."""

    def test_create_connection_authenticated_from_dict(self):
        """Create ConnectionAuthenticatedEvent from Foundation normalized dict."""
        from foundation.events import ConnectionAuthenticatedEvent

        data = {
            "type": "connection.authenticated",
            "ts": 1737200000000,
            "gameId": None,
            "seq": 5,
            "data": {
                "player_id": "did:privy:test123",
                "username": "TestPlayer",
                "hasUsername": True,
            },
        }

        event = ConnectionAuthenticatedEvent.from_dict(data)

        assert event.type == "connection.authenticated"
        assert event.player_id == "did:privy:test123"
        assert event.username == "TestPlayer"
        assert event.has_username is True


# =============================================================================
# PHASE 4: PlayerTradeEvent Tests
# =============================================================================


class TestPlayerTradeEvent:
    """Test PlayerTradeEvent dataclass."""

    def test_create_player_trade_from_dict(self):
        """Create PlayerTradeEvent from Foundation normalized dict."""
        from foundation.events import PlayerTradeEvent

        data = {
            "type": "player.trade",
            "ts": 1737200000000,
            "gameId": "20260118-abc123",
            "seq": 100,
            "data": {
                "username": "TraderBob",
                "type": "buy",
                "qty": 0.5,
                "price": 1.25,
                "playerId": "did:privy:bob",
            },
        }

        event = PlayerTradeEvent.from_dict(data)

        assert event.type == "player.trade"
        assert event.username == "TraderBob"
        assert event.trade_type == "buy"
        assert event.qty == 0.5
        assert event.price == 1.25
        assert event.player_id == "did:privy:bob"


# =============================================================================
# PHASE 5: SidebetEvent Tests
# =============================================================================


class TestSidebetEvent:
    """Test SidebetEvent dataclass."""

    def test_create_sidebet_placed_from_dict(self):
        """Create SidebetEvent from Foundation normalized dict."""
        from foundation.events import SidebetEvent

        data = {
            "type": "sidebet.placed",
            "ts": 1737200000000,
            "gameId": "20260118-abc123",
            "seq": 75,
            "data": {
                "amount": 0.05,
                "prediction": "higher",
                "targetTick": 20,
            },
        }

        event = SidebetEvent.from_dict(data)

        assert event.type == "sidebet.placed"
        assert event.amount == 0.05
        assert event.prediction == "higher"
        assert event.target_tick == 20


# =============================================================================
# PHASE 6: SidebetResultEvent Tests
# =============================================================================


class TestSidebetResultEvent:
    """Test SidebetResultEvent dataclass."""

    def test_create_sidebet_result_from_dict(self):
        """Create SidebetResultEvent from Foundation normalized dict."""
        from foundation.events import SidebetResultEvent

        data = {
            "type": "sidebet.result",
            "ts": 1737200000000,
            "gameId": "20260118-abc123",
            "seq": 80,
            "data": {
                "won": True,
                "payout": 0.095,
                "prediction": "higher",
            },
        }

        event = SidebetResultEvent.from_dict(data)

        assert event.type == "sidebet.result"
        assert event.won is True
        assert event.payout == 0.095
        assert event.prediction == "higher"


# =============================================================================
# PHASE 7: RawEvent Tests
# =============================================================================


class TestRawEvent:
    """Test RawEvent for unknown event types."""

    def test_create_raw_event_preserves_all_data(self):
        """RawEvent preserves all data from unknown events."""
        from foundation.events import RawEvent

        data = {
            "type": "raw.unknownEvent",
            "ts": 1737200000000,
            "gameId": "test",
            "seq": 999,
            "data": {
                "custom_field": "custom_value",
                "nested": {"a": 1, "b": 2},
            },
        }

        event = RawEvent.from_dict(data)

        assert event.type == "raw.unknownEvent"
        assert event.ts == 1737200000000
        assert event.game_id == "test"
        assert event.data["custom_field"] == "custom_value"
        assert event.data["nested"]["a"] == 1


# =============================================================================
# PHASE 8: Event Factory Tests
# =============================================================================


class TestEventFactory:
    """Test event factory for parsing mixed event types."""

    def test_parse_event_returns_correct_type(self):
        """parse_event returns correct typed event class."""
        from foundation.events import (
            ConnectionAuthenticatedEvent,
            GameTickEvent,
            PlayerStateEvent,
            PlayerTradeEvent,
            RawEvent,
            parse_event,
        )

        game_tick_data = {"type": "game.tick", "ts": 1000, "seq": 1, "gameId": "g1", "data": {}}
        player_state_data = {
            "type": "player.state",
            "ts": 1000,
            "seq": 2,
            "gameId": "g1",
            "data": {},
        }
        auth_data = {"type": "connection.authenticated", "ts": 1000, "seq": 3, "data": {}}
        trade_data = {"type": "player.trade", "ts": 1000, "seq": 4, "gameId": "g1", "data": {}}
        raw_data = {"type": "raw.unknown", "ts": 1000, "seq": 5, "data": {"x": 1}}

        assert isinstance(parse_event(game_tick_data), GameTickEvent)
        assert isinstance(parse_event(player_state_data), PlayerStateEvent)
        assert isinstance(parse_event(auth_data), ConnectionAuthenticatedEvent)
        assert isinstance(parse_event(trade_data), PlayerTradeEvent)
        assert isinstance(parse_event(raw_data), RawEvent)

    def test_parse_event_handles_missing_data(self):
        """parse_event handles missing data gracefully."""
        from foundation.events import GameTickEvent, parse_event

        # Minimal data
        data = {"type": "game.tick", "ts": 1000, "seq": 1}

        event = parse_event(data)

        assert isinstance(event, GameTickEvent)
        assert event.game_id is None
