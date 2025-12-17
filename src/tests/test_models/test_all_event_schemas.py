"""
Tests for All Event Schemas (Issues #3-8)

Comprehensive tests for:
- Issue #3: UsernameStatus
- Issue #4: PlayerLeaderboardPosition
- Issue #5: NewTrade
- Issue #6: SidebetRequest/SidebetResponse
- Issue #7: BuyOrderRequest/SellOrderRequest/TradeOrderResponse
- Issue #8: System events
"""

import sys
from decimal import Decimal

sys.path.insert(0, "/home/nomad/Desktop/VECTRA-PLAYER/src")

from models.events import (
    AuthEvent,
    # Issue #7
    BuyOrderRequest,
    ConnectionEvent,
    GameLifecycleEvent,
    NewTrade,
    # Issue #4
    PlayerLeaderboardPosition,
    SellOrderRequest,
    SessionEvent,
    # Issue #6
    SidebetRequest,
    SidebetResponse,
    SystemEvent,
    # Issue #8
    SystemEventType,
    TradeOrderResponse,
    # Issue #3
    UsernameStatus,
)

# =============================================================================
# ISSUE #3: UsernameStatus
# =============================================================================


class TestUsernameStatus:
    """Tests for usernameStatus event."""

    def test_basic_payload(self):
        """Parse basic usernameStatus payload."""
        data = {
            "id": "did:privy:cmaibr7rt0094jp0mc2mbpfu4",
            "hasUsername": True,
            "username": "Dutch",
        }
        event = UsernameStatus(**data)

        assert event.id == "did:privy:cmaibr7rt0094jp0mc2mbpfu4"
        assert event.username == "Dutch"
        assert event.hasUsername is True

    def test_no_username_set(self):
        """Handle player without username."""
        data = {
            "id": "did:privy:anon123",
            "hasUsername": False,
            "username": None,
        }
        event = UsernameStatus(**data)

        assert event.username is None
        assert event.hasUsername is False
        assert event.display_name == "Anonymous"

    def test_is_authenticated(self):
        """Test is_authenticated property."""
        authenticated = UsernameStatus(id="did:privy:test", hasUsername=True)
        assert authenticated.is_authenticated is True


# =============================================================================
# ISSUE #4: PlayerLeaderboardPosition
# =============================================================================


class TestPlayerLeaderboardPosition:
    """Tests for playerLeaderboardPosition event."""

    def test_full_payload(self):
        """Parse complete playerLeaderboardPosition payload."""
        data = {
            "success": True,
            "period": "7d",
            "sortDirection": "highest",
            "playerFound": True,
            "rank": 1164,
            "total": 2595,
            "playerEntry": {
                "playerId": "did:privy:cmaibr7rt0094jp0mc2mbpfu4",
                "username": "Dutch",
                "pnl": -0.015559657,
            },
            "surroundingEntries": [],
        }
        event = PlayerLeaderboardPosition(**data)

        assert event.success is True
        assert event.rank == 1164
        assert event.total == 2595
        assert event.playerEntry.username == "Dutch"
        assert event.playerEntry.pnl == Decimal("-0.015559657")

    def test_percentile_calculation(self):
        """Test percentile property."""
        event = PlayerLeaderboardPosition(
            success=True,
            rank=100,
            total=1000,
        )
        # Rank 100 of 1000 = top 10%, percentile = 90%
        assert event.percentile == 90.0

    def test_player_not_found(self):
        """Handle player not on leaderboard."""
        event = PlayerLeaderboardPosition(
            success=True,
            playerFound=False,
        )
        assert event.playerFound is False
        assert event.rank is None
        assert event.percentile is None


# =============================================================================
# ISSUE #5: NewTrade
# =============================================================================


class TestNewTrade:
    """Tests for standard/newTrade event."""

    def test_buy_trade(self):
        """Parse buy trade event."""
        data = {
            "playerId": "did:privy:test123",
            "type": "BUY",
            "amount": 0.001,
            "price": 1.234,
            "timestamp": 1765069123456,
        }
        event = NewTrade(**data)

        assert event.playerId == "did:privy:test123"
        assert event.type == "BUY"
        assert event.amount == Decimal("0.001")
        assert event.price == Decimal("1.234")
        assert event.is_buy is True

    def test_sell_trade(self):
        """Parse sell trade event."""
        data = {
            "playerId": "did:privy:test456",
            "type": "SELL",
            "amount": 0.5,
            "price": 2.5,
            "timestamp": 1765069123456,
        }
        event = NewTrade(**data)

        assert event.type == "SELL"
        assert event.is_buy is False


# =============================================================================
# ISSUE #6: Sidebet Events
# =============================================================================


class TestSidebetEvents:
    """Tests for sidebet request/response."""

    def test_sidebet_request(self):
        """Parse sidebet request."""
        data = {
            "target": 10,
            "betSize": 0.001,
        }
        request = SidebetRequest(**data)

        assert request.target == 10
        assert request.betSize == Decimal("0.001")

    def test_sidebet_response_success(self):
        """Parse successful sidebet response."""
        data = {
            "success": True,
            "timestamp": 1765068967229,
        }
        response = SidebetResponse(**data)

        assert response.success is True
        assert response.timestamp == 1765068967229

    def test_sidebet_response_failure(self):
        """Parse failed sidebet response."""
        data = {
            "success": False,
            "timestamp": 1765068967229,
            "error": "Insufficient balance",
        }
        response = SidebetResponse(**data)

        assert response.success is False
        assert response.error == "Insufficient balance"

    def test_latency_calculation(self):
        """Test latency calculation."""
        response = SidebetResponse(
            success=True,
            timestamp=1765068967000,  # Server time
        )
        client_time = 1765068967250  # Client received 250ms later
        latency = response.calculate_latency(client_time)
        assert latency == 250


# =============================================================================
# ISSUE #7: Trade Order Events
# =============================================================================


class TestTradeOrderEvents:
    """Tests for buy/sell order events."""

    def test_buy_order_request(self):
        """Parse buy order request."""
        request = BuyOrderRequest(amount=Decimal("0.001"))
        assert request.amount == Decimal("0.001")

    def test_sell_order_request(self):
        """Parse sell order request."""
        request = SellOrderRequest(percentage=50)
        assert request.percentage == 50

    def test_trade_response_success(self):
        """Parse successful trade response."""
        data = {
            "success": True,
            "executedPrice": 1.234,
            "timestamp": 1765069123456,
        }
        response = TradeOrderResponse(**data)

        assert response.success is True
        assert response.executedPrice == Decimal("1.234")

    def test_trade_response_with_fee(self):
        """Parse trade response with fee info."""
        data = {
            "success": True,
            "executedPrice": 1.5,
            "timestamp": 1765069123456,
            "amount": 0.001,
            "fee": 0.00001,
        }
        response = TradeOrderResponse(**data)

        assert response.amount == Decimal("0.001")
        assert response.fee == Decimal("0.00001")


# =============================================================================
# ISSUE #8: System Events
# =============================================================================


class TestSystemEvents:
    """Tests for system lifecycle events."""

    def test_basic_system_event(self):
        """Create basic system event."""
        event = SystemEvent(
            event_type=SystemEventType.CONNECT,
            details={"url": "wss://backend.rugs.fun"},
        )

        assert event.event_type == SystemEventType.CONNECT
        assert event.is_connection_event is True
        assert event.is_error is False

    def test_connection_event(self):
        """Test connection event specialization."""
        event = ConnectionEvent(
            event_type=SystemEventType.CONNECT,
            url="wss://backend.rugs.fun",
            latency_ms=50,
        )

        assert event.url == "wss://backend.rugs.fun"
        assert event.latency_ms == 50

    def test_auth_event(self):
        """Test authentication event."""
        event = AuthEvent(
            event_type=SystemEventType.AUTH_SUCCESS,
            player_id="did:privy:test",
            username="TestUser",
        )

        assert event.player_id == "did:privy:test"
        assert event.username == "TestUser"
        assert event.is_error is False

    def test_auth_failure_is_error(self):
        """Auth failure should be flagged as error."""
        event = AuthEvent(
            event_type=SystemEventType.AUTH_FAILURE,
            error_message="Wallet signature invalid",
        )

        assert event.is_error is True

    def test_game_lifecycle_event(self):
        """Test game start/end events."""
        event = GameLifecycleEvent(
            event_type=SystemEventType.GAME_START,
            game_id="20251215-test123",
            tick_count=0,
            price=Decimal("1.0"),
        )

        assert event.game_id == "20251215-test123"
        assert event.event_type == SystemEventType.GAME_START

    def test_session_event(self):
        """Test session boundary events."""
        event = SessionEvent(
            event_type=SystemEventType.SESSION_END,
            session_id="session-abc123",
            event_count=1500,
            duration_seconds=300.5,
        )

        assert event.session_id == "session-abc123"
        assert event.event_count == 1500


# =============================================================================
# IMPORT TEST
# =============================================================================


class TestModuleImports:
    """Verify all schemas can be imported."""

    def test_all_imports(self):
        """Ensure all exports are accessible."""
        from models.events import (
            GameStateUpdate,
            NewTrade,
            PlayerLeaderboardPosition,
            PlayerUpdate,
            SidebetResponse,
            SystemEvent,
            TradeOrderResponse,
            UsernameStatus,
        )

        # Just verify they're all classes
        assert callable(GameStateUpdate)
        assert callable(PlayerUpdate)
        assert callable(UsernameStatus)
        assert callable(PlayerLeaderboardPosition)
        assert callable(NewTrade)
        assert callable(SidebetResponse)
        assert callable(TradeOrderResponse)
        assert callable(SystemEvent)
