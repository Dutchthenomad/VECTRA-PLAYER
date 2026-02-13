"""
Tests for AuthenticationWaiter - Event-driven authentication with exponential backoff.

TDD: Tests written BEFORE implementation.
"""

import asyncio
import time

import pytest

# =============================================================================
# PHASE 1: AuthenticationState Tests
# =============================================================================


class TestAuthenticationState:
    """Test AuthenticationState dataclass."""

    def test_initial_state_has_no_identity(self):
        """Fresh AuthenticationState has no player identity."""
        from foundation.auth_waiter import AuthenticationState

        state = AuthenticationState()

        assert state.username is None
        assert state.player_id is None
        assert state.game_id is None
        assert state.wallet_address is None

    def test_is_fully_authenticated_requires_username_and_player_id(self):
        """is_fully_authenticated returns True only when both username and player_id are set."""
        from foundation.auth_waiter import AuthenticationState

        state = AuthenticationState()
        assert state.is_fully_authenticated is False

        state.username = "TestPlayer"
        assert state.is_fully_authenticated is False

        state.player_id = "did:privy:test123"
        assert state.is_fully_authenticated is True

    def test_has_game_data_returns_true_when_game_id_present(self):
        """has_game_data returns True when game_id is set."""
        from foundation.auth_waiter import AuthenticationState

        state = AuthenticationState()
        assert state.has_game_data is False

        state.game_id = "20260118-abc123"
        assert state.has_game_data is True

    def test_to_dict_returns_all_fields(self):
        """to_dict returns dictionary with all fields."""
        from foundation.auth_waiter import AuthenticationState

        state = AuthenticationState(
            username="Bob",
            player_id="did:privy:xyz",
            game_id="20260118-game",
            wallet_address="SoLaNa123abc",
        )

        result = state.to_dict()

        assert result == {
            "username": "Bob",
            "player_id": "did:privy:xyz",
            "game_id": "20260118-game",
            "wallet_address": "SoLaNa123abc",
        }


# =============================================================================
# PHASE 2: Event Extraction Tests
# =============================================================================


class TestEventExtraction:
    """Test extraction of player identity from various event types."""

    def test_extract_from_connection_authenticated_event_normalized(self):
        """Extract from connection.authenticated with normalized field names."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        event = {
            "type": "connection.authenticated",
            "data": {
                "username": "Alice",
                "player_id": "did:privy:alice123",  # Normalized field name
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        assert username == "Alice"
        assert player_id == "did:privy:alice123"

    def test_extract_from_connection_authenticated_event_raw(self):
        """Extract from connection.authenticated with raw field names (usernameStatus)."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        # Raw usernameStatus data has "id", not "player_id"
        event = {
            "type": "connection.authenticated",
            "data": {
                "id": "did:privy:bob456",  # RAW field from usernameStatus
                "username": "Bob",
                "hasUsername": True,
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        assert username == "Bob"
        assert player_id == "did:privy:bob456"

    def test_player_state_does_not_contain_identity(self):
        """player.state (playerUpdate) does NOT contain username/player_id."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        # playerUpdate only has balance/position data, no identity
        event = {
            "type": "player.state",
            "data": {
                "cash": 3.967,
                "positionQty": 0.222,
                "avgCost": 1.259,
                "cumulativePnL": 0.264,
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        # Should return None, None - playerUpdate has no identity
        assert username is None
        assert player_id is None

    def test_extract_from_game_tick_leaderboard(self):
        """Extract player from leaderboard when wallet matches."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)
        waiter.set_wallet_address("cmaibr_wallet_partial")

        event = {
            "type": "game.tick",
            "gameId": "20260118-game123",
            "data": {
                "leaderboard": [
                    {
                        "id": "did:privy:cmaibr_wallet_partial_suffix",
                        "username": "Charlie",
                        "position": "BUY",
                        "positionQty": 1.5,
                    },
                    {
                        "id": "did:privy:other_player",
                        "username": "OtherPlayer",
                        "position": "SELL",
                        "positionQty": 0.5,
                    },
                ],
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        assert username == "Charlie"
        assert player_id == "did:privy:cmaibr_wallet_partial_suffix"

    def test_extract_from_player_leaderboard_position(self):
        """Extract from playerLeaderboardPosition event - contains YOUR identity."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        # This event contains YOUR identity in playerEntry
        event = {
            "type": "player.leaderboard",
            "data": {
                "success": True,
                "period": "7d",
                "playerEntry": {
                    "playerId": "did:privy:dutch123",
                    "username": "Dutch",
                    "pnl": -0.015,
                },
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        assert username == "Dutch"
        assert player_id == "did:privy:dutch123"

    def test_game_tick_without_wallet_returns_none(self):
        """game.tick leaderboard WITHOUT wallet match returns None (no hasActiveTrades fallback)."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)
        # No wallet address set - should NOT fall back to hasActiveTrades

        event = {
            "type": "game.tick",
            "gameId": "20260118-game123",
            "data": {
                "leaderboard": [
                    {
                        "id": "did:privy:other_player",
                        "username": "SomeoneElse",
                        "hasActiveTrades": True,
                    },
                ],
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        # Should NOT pick up another player just because they have active trades
        assert username is None
        assert player_id is None

    def test_connection_status_not_used_for_identity(self):
        """connection.status is not used for identity extraction."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        # connection.status is not a reliable identity source
        event = {
            "type": "connection.status",
            "data": {
                "username": "Dave",
                "playerId": "did:privy:dave789",
            },
        }

        username, player_id = waiter._extract_player_from_event(event)

        # Should return None - only connection.authenticated and leaderboard are used
        assert username is None
        assert player_id is None

    def test_extract_returns_none_for_unknown_event_type(self):
        """Unknown event type returns (None, None)."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        event = {
            "type": "some.other.event",
            "data": {"irrelevant": "data"},
        }

        username, player_id = waiter._extract_player_from_event(event)

        assert username is None
        assert player_id is None

    def test_extract_game_id_from_event(self):
        """Game ID is extracted and stored in state."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        event = {
            "type": "game.tick",
            "gameId": "20260118-xyz789",
            "data": {"leaderboard": []},
        }

        waiter._update_state_from_event(event)

        assert waiter.state.game_id == "20260118-xyz789"


# =============================================================================
# PHASE 3: Exponential Backoff Tests
# =============================================================================


class TestExponentialBackoff:
    """Test exponential backoff calculation."""

    def test_initial_interval_is_configurable(self):
        """Initial check interval matches configuration."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(
            max_wait_seconds=60.0,
            initial_check_interval=0.25,
        )

        assert waiter.initial_interval == 0.25

    def test_backoff_multiplier_is_configurable(self):
        """Backoff multiplier matches configuration."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(
            max_wait_seconds=60.0,
            backoff_multiplier=2.0,
        )

        assert waiter.backoff_multiplier == 2.0

    def test_max_interval_caps_exponential_growth(self):
        """Max interval prevents unbounded growth."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(
            max_wait_seconds=60.0,
            initial_check_interval=1.0,
            max_check_interval=3.0,
            backoff_multiplier=2.0,
        )

        # Simulate backoff calculation
        interval = waiter.initial_interval
        for _ in range(10):  # Many iterations
            interval = min(interval * waiter.backoff_multiplier, waiter.max_interval)

        assert interval == 3.0  # Capped at max_check_interval


# =============================================================================
# PHASE 4: Authentication Flow Tests (Async)
# =============================================================================


class TestAuthenticationFlow:
    """Test complete authentication flow."""

    @pytest.mark.asyncio
    async def test_immediate_authentication_exits_early(self):
        """Immediate auth event exits before timeout."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        # Simulate auth event arriving immediately
        async def simulate_auth():
            await asyncio.sleep(0.1)
            waiter._update_state_from_event(
                {
                    "type": "connection.authenticated",
                    "data": {"username": "FastUser", "player_id": "did:fast"},
                }
            )
            waiter._event_received.set()

        asyncio.create_task(simulate_auth())

        start = time.monotonic()
        state = await waiter.wait_for_authentication()
        elapsed = time.monotonic() - start

        assert state.is_fully_authenticated
        assert state.username == "FastUser"
        assert elapsed < 1.0  # Should exit well before 60s

    @pytest.mark.asyncio
    async def test_timeout_with_game_data_returns_partial_state(self):
        """Timeout with game data returns partial state (read-only mode)."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(
            max_wait_seconds=0.5,  # Short timeout for test
            initial_check_interval=0.1,
        )

        # Simulate game data arriving but no player identity
        async def simulate_game_data():
            await asyncio.sleep(0.05)
            waiter._update_state_from_event(
                {
                    "type": "game.tick",
                    "gameId": "20260118-test",
                    "data": {"leaderboard": []},
                }
            )

        asyncio.create_task(simulate_game_data())

        state = await waiter.wait_for_authentication()

        assert not state.is_fully_authenticated
        assert state.has_game_data
        assert state.game_id == "20260118-test"

    @pytest.mark.asyncio
    async def test_timeout_without_game_data_raises_error(self):
        """Timeout without any game data raises TimeoutError."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(
            max_wait_seconds=0.3,  # Very short timeout
            initial_check_interval=0.1,
        )

        with pytest.raises(TimeoutError) as exc_info:
            await waiter.wait_for_authentication()

        assert "no game activity" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_delayed_authentication_succeeds_within_timeout(self):
        """Authentication arriving within timeout succeeds."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(
            max_wait_seconds=2.0,
            initial_check_interval=0.1,
        )

        # Simulate delayed auth using connection.authenticated (usernameStatus)
        async def simulate_delayed_auth():
            await asyncio.sleep(0.5)
            waiter._update_state_from_event(
                {
                    "type": "connection.authenticated",
                    "data": {
                        "id": "did:delayed",  # Raw field from usernameStatus
                        "username": "DelayedUser",
                        "hasUsername": True,
                    },
                }
            )
            waiter._event_received.set()

        asyncio.create_task(simulate_delayed_auth())

        state = await waiter.wait_for_authentication()

        assert state.is_fully_authenticated
        assert state.username == "DelayedUser"

    @pytest.mark.asyncio
    async def test_wallet_address_can_be_set(self):
        """Wallet address can be set for player matching."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        waiter.set_wallet_address("0xABC123")

        assert waiter.state.wallet_address == "0xABC123"


# =============================================================================
# PHASE 5: Integration with Existing EventBus (Optional)
# =============================================================================


class TestEventBusIntegration:
    """Test integration with existing EventBus (callback-based)."""

    def test_callback_updates_state(self):
        """Event callback properly updates authentication state."""
        from foundation.auth_waiter import AuthenticationWaiter

        waiter = AuthenticationWaiter(max_wait_seconds=60.0)

        # Simulate callback invocation (synchronous)
        event = {
            "type": "connection.authenticated",
            "data": {"username": "CallbackUser", "player_id": "did:callback"},
        }

        # This is a sync method that EventBus would call
        waiter._update_state_from_event(event)

        assert waiter.state.username == "CallbackUser"
        assert waiter.state.player_id == "did:callback"
        assert waiter.state.is_fully_authenticated
