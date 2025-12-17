"""
Tests for GameStateUpdate Pydantic Schema

GitHub Issue: #1
TDD: Tests written FIRST to validate schema design
"""

# Import will fail until schema is in Python path
import sys
from decimal import Decimal

sys.path.insert(0, "/home/nomad/Desktop/VECTRA-PLAYER/src")

from models.events.game_state_update import (
    AvailableShitcoin,
    GameHistoryEntry,
    GameStateUpdate,
    LeaderboardEntry,
    PartialPrices,
    Rugpool,
)


class TestGameStateUpdateMinimal:
    """Test minimal valid payloads."""

    def test_minimal_payload(self):
        """Minimum required fields parse successfully."""
        data = {
            "gameId": "20251215-test123",
            "active": True,
            "rugged": False,
            "price": 1.5,
            "tickCount": 100,
        }
        event = GameStateUpdate(**data)

        assert event.gameId == "20251215-test123"
        assert event.active is True
        assert event.rugged is False
        assert event.price == Decimal("1.5")
        assert event.tickCount == 100

    def test_defaults_applied(self):
        """Missing optional fields get defaults."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
        }
        event = GameStateUpdate(**data)

        assert event.gameVersion == "v3"
        assert event.cooldownTimer == 0
        assert event.cooldownPaused is False
        assert event.pauseMessage == ""
        assert event.allowPreRoundBuys is False
        assert event.connectedPlayers == 0
        assert event.leaderboard == []
        assert event.gameHistory == []


class TestDecimalCoercion:
    """Test float to Decimal conversion."""

    def test_price_coerced_to_decimal(self):
        """Float price becomes Decimal."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 0.01978688651688796,  # Float from server
            "tickCount": 17,
        }
        event = GameStateUpdate(**data)

        assert isinstance(event.price, Decimal)
        assert event.price == Decimal("0.01978688651688796")

    def test_statistics_coerced(self):
        """Statistical fields coerced to Decimal."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
            "averageMultiplier": 6.286986541653673,
            "highestToday": 1026.429049568061,
        }
        event = GameStateUpdate(**data)

        assert isinstance(event.averageMultiplier, Decimal)
        assert isinstance(event.highestToday, Decimal)

    def test_god_candle_coerced(self):
        """God candle fields coerced to Decimal."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
            "godCandle2x": 2.5,
            "godCandle10x": 10.123,
            "godCandle50x": 50.999,
        }
        event = GameStateUpdate(**data)

        assert event.godCandle2x == Decimal("2.5")
        assert event.godCandle10x == Decimal("10.123")
        assert event.godCandle50x == Decimal("50.999")


class TestLeaderboardEntry:
    """Test leaderboard entry parsing."""

    def test_full_leaderboard_entry(self):
        """Complete leaderboard entry parses correctly."""
        data = {
            "id": "did:privy:cmigqkf0f00x4jm0cuxvdrunq",
            "username": "Fannyman",
            "level": 43,
            "pnl": 0.264879755,
            "regularPnl": 0.264879755,
            "sidebetPnl": 0,
            "shortPnl": 0,
            "pnlPercent": 105.38,
            "hasActiveTrades": True,
            "positionQty": 0.2222919,
            "avgCost": 1.259605046,
            "totalInvested": 0.251352892,
            "sidebetActive": None,
            "sideBet": None,
            "shortPosition": None,
            "selectedCoin": None,
            "position": 1,
        }
        entry = LeaderboardEntry(**data)

        assert entry.id == "did:privy:cmigqkf0f00x4jm0cuxvdrunq"
        assert entry.username == "Fannyman"
        assert entry.level == 43
        assert entry.pnl == Decimal("0.264879755")
        assert entry.hasActiveTrades is True
        assert entry.positionQty == Decimal("0.2222919")
        assert entry.position == 1

    def test_leaderboard_entry_with_sidebet(self):
        """Leaderboard entry with active sidebet."""
        data = {
            "id": "did:privy:test",
            "pnl": 0.1,
            "sidebetActive": True,
            "sideBet": {
                "target": 10,
                "betSize": 0.001,
                "startTick": 50,
                "endTick": 90,
            },
        }
        entry = LeaderboardEntry(**data)

        assert entry.sidebetActive is True
        assert entry.sideBet is not None
        assert entry.sideBet.target == 10
        assert entry.sideBet.betSize == Decimal("0.001")

    def test_leaderboard_null_username(self):
        """Username can be null (not set by player)."""
        data = {
            "id": "did:privy:test",
            "username": None,
            "pnl": 0,
        }
        entry = LeaderboardEntry(**data)

        assert entry.username is None


class TestPartialPrices:
    """Test partial prices window parsing."""

    def test_partial_prices(self):
        """Partial prices window parses correctly."""
        data = {
            "startTick": 125,
            "endTick": 129,
            "values": {
                "125": 1.2749526227232495,
                "126": 1.3019525694480605,
                "127": 1.073446660724414,
                "128": 1.0654483722620864,
                "129": 1.061531247396796,
            },
        }
        partial = PartialPrices(**data)

        assert partial.startTick == 125
        assert partial.endTick == 129
        assert len(partial.values) == 5
        assert partial.values["125"] == Decimal("1.2749526227232495")


class TestGameHistoryEntry:
    """Test game history entry parsing."""

    def test_game_history_entry(self):
        """Game history entry parses correctly."""
        data = {
            "id": "20251207-1e01ac417e8043ca",
            "timestamp": 1765068982439,
            "prices": [1, 0.99, 1.01, 1.5, 2.0],
            "rugged": True,
            "rugPoint": 45.23,
        }
        entry = GameHistoryEntry(**data)

        assert entry.id == "20251207-1e01ac417e8043ca"
        assert entry.timestamp == 1765068982439
        assert entry.rugged is True
        assert entry.rugPoint == Decimal("45.23")
        assert len(entry.prices) == 5
        assert all(isinstance(p, Decimal) for p in entry.prices)


class TestAvailableShitcoin:
    """Test available coin parsing."""

    def test_available_shitcoin(self):
        """Available shitcoin parses correctly."""
        data = {
            "address": "0xPractice",
            "ticker": "FREE",
            "name": "Practice SOL",
            "max_bet": 10000,
            "max_win": 100000,
        }
        coin = AvailableShitcoin(**data)

        assert coin.address == "0xPractice"
        assert coin.ticker == "FREE"
        assert coin.max_bet == Decimal("10000")
        assert coin.max_win == Decimal("100000")


class TestRugpool:
    """Test rugpool lottery state parsing."""

    def test_basic_rugpool(self):
        """Basic rugpool state parses correctly."""
        data = {
            "rugpoolAmount": 1.025,
            "threshold": 10,
            "instarugCount": 2,
        }
        rugpool = Rugpool(**data)

        assert rugpool.rugpoolAmount == Decimal("1.025")
        assert rugpool.threshold == 10
        assert rugpool.instarugCount == 2

    def test_full_rugpool(self):
        """Full rugpool with player entries."""
        data = {
            "rugpoolAmount": 7.440795633500021,
            "threshold": 10,
            "instarugCount": 9,
            "totalEntries": 22269,
            "playersWithEntries": 155,
            "solPerEntry": 0.001,
            "maxEntriesPerPlayer": 5000,
            "playerEntries": [
                {
                    "playerId": "did:privy:test",
                    "entries": 5000,
                    "username": "testuser",
                    "percentage": 22.452736988638915,
                }
            ],
        }
        rugpool = Rugpool(**data)

        assert rugpool.totalEntries == 22269
        assert rugpool.solPerEntry == Decimal("0.001")
        assert len(rugpool.playerEntries) == 1
        assert rugpool.playerEntries[0].percentage == Decimal("22.452736988638915")


class TestFullPayload:
    """Test complete realistic payloads."""

    def test_full_game_state_update(self):
        """Complete gameStateUpdate payload from spec."""
        data = {
            "gameId": "20251210-80d2ade6a0db4338",
            "gameVersion": "v3",
            "active": True,
            "rugged": True,
            "price": 0.01978688651688796,
            "tickCount": 17,
            "cooldownTimer": 0,
            "cooldownPaused": False,
            "pauseMessage": "",
            "allowPreRoundBuys": False,
            "averageMultiplier": 6.286986541653673,
            "connectedPlayers": 190,
            "count2x": 46,
            "count10x": 8,
            "count50x": 3,
            "count100x": 1,
            "highestToday": 1026.429049568061,
            "highestTodayTimestamp": 1765260384895,
            "leaderboard": [
                {
                    "id": "did:privy:cmigqkf0f00x4jm0cuxvdrunq",
                    "username": "Fannyman",
                    "level": 43,
                    "pnl": 0.264879755,
                    "regularPnl": 0.264879755,
                    "sidebetPnl": 0,
                    "shortPnl": 0,
                    "pnlPercent": 105.38,
                    "hasActiveTrades": True,
                    "positionQty": 0.2222919,
                    "avgCost": 1.259605046,
                    "totalInvested": 0.251352892,
                    "position": 1,
                }
            ],
            "partialPrices": {
                "startTick": 10,
                "endTick": 17,
                "values": {
                    "10": 1.0,
                    "11": 1.1,
                    "12": 0.9,
                    "13": 0.8,
                    "14": 0.5,
                    "15": 0.3,
                    "16": 0.1,
                    "17": 0.02,
                },
            },
            "gameHistory": [
                {
                    "id": "20251207-test",
                    "timestamp": 1765068982439,
                    "prices": [1, 2, 3, 4, 5],
                    "rugged": True,
                    "rugPoint": 5.0,
                }
            ],
            "provablyFair": {
                "serverSeedHash": "bce190330836fffda61bdecbed6d8a83bfb7bb3a6b2bd278002a36df773c809a",
                "version": "v3",
            },
            "availableShitcoins": [
                {
                    "address": "0xPractice",
                    "ticker": "FREE",
                    "name": "Practice SOL",
                    "max_bet": 10000,
                    "max_win": 100000,
                }
            ],
        }
        event = GameStateUpdate(**data)

        # Verify core fields
        assert event.gameId == "20251210-80d2ade6a0db4338"
        assert event.active is True
        assert event.rugged is True
        assert event.price == Decimal("0.01978688651688796")
        assert event.tickCount == 17

        # Verify statistics
        assert event.connectedPlayers == 190
        assert event.count2x == 46

        # Verify nested structures
        assert len(event.leaderboard) == 1
        assert event.leaderboard[0].username == "Fannyman"

        assert event.partialPrices is not None
        assert event.partialPrices.startTick == 10

        assert len(event.gameHistory) == 1
        assert event.gameHistory[0].rugPoint == Decimal("5.0")

        assert event.provablyFair is not None
        assert event.provablyFair.version == "v3"

        assert len(event.availableShitcoins) == 1
        assert event.availableShitcoins[0].ticker == "FREE"


class TestHelperMethods:
    """Test schema helper methods."""

    def test_get_player_by_id(self):
        """Find player by ID in leaderboard."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
            "leaderboard": [
                {"id": "did:privy:player1", "pnl": 0.1, "username": "Player1"},
                {"id": "did:privy:player2", "pnl": 0.2, "username": "Player2"},
            ],
        }
        event = GameStateUpdate(**data)

        player = event.get_player_by_id("did:privy:player2")
        assert player is not None
        assert player.username == "Player2"

        # Non-existent player
        assert event.get_player_by_id("did:privy:unknown") is None

    def test_get_player_by_username(self):
        """Find player by username in leaderboard."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
            "leaderboard": [
                {"id": "did:privy:player1", "pnl": 0.1, "username": "Dutch"},
            ],
        }
        event = GameStateUpdate(**data)

        player = event.get_player_by_username("Dutch")
        assert player is not None
        assert player.id == "did:privy:player1"

    def test_is_game_active(self):
        """Test is_game_active property."""
        # Active game
        active = GameStateUpdate(gameId="test", active=True, rugged=False, price=1.0, tickCount=0)
        assert active.is_game_active is True

        # Rugged game
        rugged = GameStateUpdate(gameId="test", active=True, rugged=True, price=1.0, tickCount=0)
        assert rugged.is_game_active is False

        # Inactive game
        inactive = GameStateUpdate(
            gameId="test", active=False, rugged=False, price=1.0, tickCount=0
        )
        assert inactive.is_game_active is False

    def test_is_cooldown(self):
        """Test is_cooldown property."""
        # During game
        in_game = GameStateUpdate(gameId="test", active=True, rugged=False, price=1.0, tickCount=0)
        assert in_game.is_cooldown is False

        # In cooldown
        cooldown = GameStateUpdate(
            gameId="test",
            active=False,
            rugged=False,
            price=1.0,
            tickCount=0,
            cooldownTimer=15,
        )
        assert cooldown.is_cooldown is True


class TestForwardCompatibility:
    """Test handling of unknown fields (forward compatibility)."""

    def test_extra_fields_allowed(self):
        """Unknown fields are captured for forward compatibility."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
            "newFieldFromServer": "some_value",  # Unknown field
            "anotherNewField": 12345,
        }
        event = GameStateUpdate(**data)

        # Model should parse without error
        assert event.gameId == "test"
        # Extra fields captured
        assert hasattr(event, "newFieldFromServer") or "newFieldFromServer" in event.model_extra


class TestMetadataFields:
    """Test ingestion metadata fields."""

    def test_metadata_optional(self):
        """Metadata fields are optional (not from socket)."""
        data = {
            "gameId": "test",
            "active": True,
            "rugged": False,
            "price": 1.0,
            "tickCount": 0,
        }
        event = GameStateUpdate(**data)

        # These are None by default (added by ingestion, not socket)
        assert event.meta_ts is None
        assert event.meta_seq is None
        assert event.meta_source is None
        assert event.meta_session_id is None
