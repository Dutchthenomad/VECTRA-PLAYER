"""Tests for Pydantic models derived from Rosetta Stone v0.2.0."""

import pytest
from src.models import (
    Channel,
    DailyRecords,
    GameHistoryRecord,
    GameTick,
    LeaderboardEntry,
    PartialPrices,
    Phase,
    ProvablyFair,
    Rugpool,
    SanitizedEvent,
    SessionStats,
    ShortPosition,
    SideBet,
    Trade,
    TradeType,
)

# ---------------------------------------------------------------------------
# Reference data from Rosetta Stone Appendix D (game 20260206-003482fbeaae4ad5)
# ---------------------------------------------------------------------------

ACTIVE_TICK = {
    "gameId": "20260206-003482fbeaae4ad5",
    "active": True,
    "rugged": False,
    "price": 1.0232227021442333,
    "tickCount": 3,
    "tradeCount": 172,
    "cooldownTimer": 0,
    "cooldownPaused": False,
    "allowPreRoundBuys": False,
    "pauseMessage": "",
    "connectedPlayers": 172,
    "averageMultiplier": 15.037,
    "count2x": 52,
    "count10x": 9,
    "count50x": 1,
    "count100x": 1,
    "partialPrices": {
        "startTick": 0,
        "endTick": 3,
        "values": {"0": 1.0, "1": 1.0017, "2": 1.0171, "3": 1.0232},
    },
    "provablyFair": {
        "serverSeedHash": "2b2bcc8b4b71d70a1f69163b18f883acada7d5c12f327fb4624e0df792bee893",
        "version": "v3",
    },
    "rugpool": {"instarugCount": 6, "threshold": 10, "rugpoolAmount": 4.444},
    "leaderboard": [
        {
            "id": "did:privy:cmcl09j6b00a6l70mq2nunza1",
            "username": "Syken",
            "level": 57,
            "pnl": 0.032391178,
            "regularPnl": 0.032391178,
            "sidebetPnl": 0,
            "shortPnl": 0,
            "pnlPercent": 0.85,
            "hasActiveTrades": True,
            "positionQty": 0.762,
            "avgCost": 1.0,
            "totalInvested": 3.81,
            "position": 1,
            "selectedCoin": None,
            "sidebetActive": True,
            "sideBet": {
                "startedAtTick": 0,
                "gameId": "20260206-003482fbeaae4ad5",
                "end": 40,
                "betAmount": 3.048,
                "xPayout": 5,
                "coinAddress": "So11111111111111111111111111111111111111112",
                "bonusPortion": 3.048,
                "realPortion": 0,
            },
            "shortPosition": None,
        }
    ],
    "rugRoyale": {"status": "INACTIVE"},
}

RUGGED_TICK = {
    "gameId": "20260206-003482fbeaae4ad5",
    "active": True,
    "rugged": True,
    "price": 0.0017842710071060424,
    "tickCount": 255,
    "tradeCount": 306,
    "cooldownTimer": 0,
    "cooldownPaused": False,
    "allowPreRoundBuys": False,
    "provablyFair": {
        "serverSeedHash": "2b2bcc8b4b71d70a1f69163b18f883acada7d5c12f327fb4624e0df792bee893",
        "serverSeed": "49f5826e1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        "version": "v3",
    },
    "leaderboard": [],
    "partialPrices": {
        "startTick": 251,
        "endTick": 255,
        "values": {
            "251": 0.10974594841914126,
            "252": 0.10944535617321477,
            "253": 0.10813627770291478,
            "254": 0.10599876754314011,
            "255": 0.0017842710071060424,
        },
    },
}

COOLDOWN_TICK = {
    "gameId": "20260206-003482fbeaae4ad5",
    "cooldownTimer": 14900,
    "cooldownPaused": False,
    "allowPreRoundBuys": False,
    "connectedPlayers": 170,
    "leaderboard": [],
    "provablyFair": {
        "serverSeedHash": "abc123",
        "version": "v3",
    },
}

PRESALE_TICK = {
    "gameId": "20260206-nextgame1234567890",
    "cooldownTimer": 8500,
    "cooldownPaused": False,
    "allowPreRoundBuys": True,
    "connectedPlayers": 175,
    "leaderboard": [],
    "provablyFair": {
        "serverSeedHash": "def456",
        "version": "v3",
    },
}

RAW_BUY_TRADE = {
    "id": "7c10a169-2a5c-4f9a-8e7f-e7d0da4a1b47",
    "gameId": "20260206-003482fbeaae4ad5",
    "playerId": "did:privy:cmfl7ry7000w1ie0ck1ve8oq9",
    "price": 0.9871838027078929,
    "type": "buy",
    "qty": 0.030389477,
    "tickIndex": 37,
    "coin": "solana",
    "amount": 0.03,
    "leverage": 4,
    "bonusPortion": 0,
    "realPortion": 0.03,
    "username": "Aussiegambler",
    "level": 34,
}

RAW_SELL_TRADE = {
    "id": "f6e59f57-6f35-46db-889c-89ecaea5c672",
    "gameId": "20260206-003482fbeaae4ad5",
    "playerId": "did:privy:cmcl09j6b00a6l70mq2nunza1",
    "type": "sell",
    "price": 1.0425081084067145,
    "tickIndex": 8,
    "coin": "solana",
    "amount": 0.794391178,
    "qty": 0.762,
    "bonusPortion": 0.794391178,
    "realPortion": 0,
    "username": "Syken",
    "level": 57,
}

RAW_SHORT_OPEN = {
    "id": "35b49232-5d50-4283-8bab-be0aab8129ef",
    "gameId": "20260206-003482fbeaae4ad5",
    "playerId": "did:privy:cmj0kekh0046il80bwjmpe31d",
    "price": 1.0232227021442333,
    "type": "short_open",
    "qty": 0,
    "tickIndex": 3,
    "coin": "solana",
    "amount": 0.2,
    "username": "BANDZDAGOD",
    "level": 11,
}

RAW_GAME_HISTORY_ENTRY = {
    "id": "20260206-74fb8b07116b4d39",
    "timestamp": 1770347058350,
    "peakMultiplier": 7.070,
    "rugged": True,
    "gameVersion": "v3",
    "prices": [1.0, 1.0017, 1.0171, 0.9532],
    "globalTrades": None,
    "globalSidebets": [
        {
            "id": "cc028cdf-1234",
            "playerId": "did:privy:test1",
            "username": "JJWilliams04",
            "gameId": "20260206-74fb8b07116b4d39",
            "betAmount": 0.002,
            "xPayout": 5,
            "coinAddress": "So11111111111111111111111111111111111111112",
            "bonusPortion": 0,
            "realPortion": 0.002,
            "timestamp": 1770347007162,
            "type": "placed",
            "startedAtTick": 2,
            "end": 42,
        }
    ],
    "provablyFair": {
        "serverSeed": "49f5826e0000000000000000000000000000000000000000000000000000dead",
        "serverSeedHash": "c1709d66abcdef",
    },
}


# ---------------------------------------------------------------------------
# PartialPrices
# ---------------------------------------------------------------------------


class TestPartialPrices:
    def test_from_raw(self):
        pp = PartialPrices.from_raw(ACTIVE_TICK["partialPrices"])
        assert pp is not None
        assert pp.start_tick == 0
        assert pp.end_tick == 3
        assert len(pp.values) == 4
        assert pp.values["0"] == 1.0

    def test_from_raw_none(self):
        assert PartialPrices.from_raw(None) is None

    def test_rug_candle(self):
        pp = PartialPrices.from_raw(RUGGED_TICK["partialPrices"])
        assert pp is not None
        assert pp.start_tick == 251
        assert pp.end_tick == 255
        assert len(pp.values) == 5
        # Rug crash: 0.106 -> 0.0018
        assert pp.values["255"] == pytest.approx(0.001784, rel=1e-2)


# ---------------------------------------------------------------------------
# ProvablyFair
# ---------------------------------------------------------------------------


class TestProvablyFair:
    def test_pre_rug(self):
        pf = ProvablyFair.from_raw(ACTIVE_TICK["provablyFair"])
        assert pf is not None
        assert pf.server_seed_hash.startswith("2b2bcc")
        assert pf.version == "v3"
        assert pf.server_seed is None

    def test_post_rug_seed_reveal(self):
        pf = ProvablyFair.from_raw(RUGGED_TICK["provablyFair"])
        assert pf is not None
        assert pf.server_seed is not None
        assert pf.server_seed.startswith("49f5826e")

    def test_from_raw_none(self):
        assert ProvablyFair.from_raw(None) is None


# ---------------------------------------------------------------------------
# Rugpool
# ---------------------------------------------------------------------------


class TestRugpool:
    def test_from_raw(self):
        rp = Rugpool.from_raw(ACTIVE_TICK["rugpool"])
        assert rp is not None
        assert rp.instarug_count == 6
        assert rp.threshold == 10
        assert rp.rugpool_amount == pytest.approx(4.444)

    def test_from_raw_none(self):
        assert Rugpool.from_raw(None) is None


# ---------------------------------------------------------------------------
# SideBet
# ---------------------------------------------------------------------------


class TestSideBet:
    def test_from_raw(self):
        raw = ACTIVE_TICK["leaderboard"][0]["sideBet"]
        sb = SideBet.from_raw(raw)
        assert sb is not None
        assert sb.started_at_tick == 0
        assert sb.end == 40  # Hardcoded 40-tick window
        assert sb.bet_amount == 3.048
        assert sb.x_payout == 5  # Always 5x
        assert sb.bonus_portion == 3.048
        assert sb.real_portion == 0

    def test_from_raw_none(self):
        assert SideBet.from_raw(None) is None


# ---------------------------------------------------------------------------
# ShortPosition
# ---------------------------------------------------------------------------


class TestShortPosition:
    def test_from_raw(self):
        raw = {
            "amount": 0.2,
            "entryPrice": 1.023,
            "entryTick": 3,
            "currentValue": 0.2079,
            "pnl": 0.0079,
            "coinAddress": "So11111111111111111111111111111111111111112",
            "bonusPortion": 0,
            "realPortion": 0.2,
        }
        sp = ShortPosition.from_raw(raw)
        assert sp is not None
        assert sp.amount == 0.2
        assert sp.entry_price == pytest.approx(1.023)
        assert sp.pnl == pytest.approx(0.0079)

    def test_from_raw_none(self):
        assert ShortPosition.from_raw(None) is None


# ---------------------------------------------------------------------------
# LeaderboardEntry
# ---------------------------------------------------------------------------


class TestLeaderboardEntry:
    def test_from_raw(self):
        raw = ACTIVE_TICK["leaderboard"][0]
        entry = LeaderboardEntry.from_raw(raw)
        assert entry.id == "did:privy:cmcl09j6b00a6l70mq2nunza1"
        assert entry.username == "Syken"
        assert entry.level == 57
        assert entry.pnl == pytest.approx(0.032391178)
        assert entry.position == 1
        assert entry.has_active_trades is True
        assert entry.side_bet is not None
        assert entry.side_bet.end == 40
        assert entry.short_position is None

    def test_practice_detection_real_sol(self):
        entry = LeaderboardEntry.from_raw(ACTIVE_TICK["leaderboard"][0])
        assert entry.is_practice is False  # selectedCoin is None = SOL

    def test_practice_detection_practice_token(self):
        raw = {**ACTIVE_TICK["leaderboard"][0]}
        raw["selectedCoin"] = {"address": "0xPractice", "ticker": "FREE"}
        entry = LeaderboardEntry.from_raw(raw)
        assert entry.is_practice is True


# ---------------------------------------------------------------------------
# GameTick
# ---------------------------------------------------------------------------


class TestGameTick:
    def test_active_tick(self):
        tick = GameTick.from_raw(ACTIVE_TICK, Phase.ACTIVE)
        assert tick.game_id == "20260206-003482fbeaae4ad5"
        assert tick.phase == Phase.ACTIVE
        assert tick.active is True
        assert tick.rugged is False
        assert tick.price == pytest.approx(1.0232, rel=1e-3)
        assert tick.tick_count == 3
        assert tick.trade_count == 172
        assert tick.partial_prices is not None
        assert tick.provably_fair is not None
        assert tick.provably_fair.server_seed is None
        assert tick.rugpool is not None
        assert len(tick.leaderboard) == 1
        assert tick.has_god_candle is False

    def test_rugged_tick(self):
        tick = GameTick.from_raw(RUGGED_TICK, Phase.RUGGED)
        assert tick.phase == Phase.RUGGED
        assert tick.rugged is True
        assert tick.price == pytest.approx(0.001784, rel=1e-2)
        assert tick.tick_count == 255
        assert tick.provably_fair is not None
        assert tick.provably_fair.server_seed is not None

    def test_cooldown_tick(self):
        tick = GameTick.from_raw(COOLDOWN_TICK, Phase.COOLDOWN)
        assert tick.phase == Phase.COOLDOWN
        assert tick.cooldown_timer == 14900
        assert tick.active is False
        assert tick.rugged is False

    def test_presale_tick(self):
        tick = GameTick.from_raw(PRESALE_TICK, Phase.PRESALE)
        assert tick.phase == Phase.PRESALE
        assert tick.allow_pre_round_buys is True
        assert tick.cooldown_timer == 8500

    def test_god_candle_flag(self):
        data = {
            **ACTIVE_TICK,
            "highestToday": 1122.278,
            "highestTodayTimestamp": 1770346597293,
            "highestTodayGameId": "20260206-37b5",
            "highestTodayServerSeed": "3b0be421",
            "godCandle2x": 15.5,
            "godCandle2xTimestamp": 1770346598019,
            "godCandle2xGameId": "20260206-43cb",
            "godCandle2xServerSeed": "bfb75645",
            "godCandle2xMassiveJump": [10.0, 15.5],
            "godCandle10x": None,
            "godCandle50x": None,
        }
        tick = GameTick.from_raw(data, Phase.ACTIVE)
        assert tick.has_god_candle is True
        assert tick.daily_records is not None
        assert tick.daily_records.highest_today == pytest.approx(1122.278)
        assert tick.daily_records.god_candle_2x.multiplier == pytest.approx(15.5)
        assert tick.daily_records.god_candle_10x.multiplier is None


# ---------------------------------------------------------------------------
# SessionStats
# ---------------------------------------------------------------------------


class TestSessionStats:
    def test_from_raw(self):
        stats = SessionStats.from_raw(ACTIVE_TICK)
        assert stats.connected_players == 172
        assert stats.average_multiplier == pytest.approx(15.037)
        assert stats.count_2x == 52
        assert stats.count_10x == 9
        assert stats.count_50x == 1
        assert stats.count_100x == 1

    def test_cooldown_partial(self):
        stats = SessionStats.from_raw(COOLDOWN_TICK)
        assert stats.connected_players == 170
        assert stats.average_multiplier is None


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


class TestTrade:
    def test_buy(self):
        t = Trade.from_raw(RAW_BUY_TRADE)
        assert t.type == TradeType.BUY
        assert t.game_id == "20260206-003482fbeaae4ad5"
        assert t.leverage == 4
        assert t.amount == 0.03
        assert t.qty == pytest.approx(0.030389477)
        assert t.real_portion == 0.03
        assert t.bonus_portion == 0
        # Annotations default to unannotated
        assert t.is_forced_sell is False
        assert t.is_practice is False
        assert t.token_type == "unknown"

    def test_sell(self):
        t = Trade.from_raw(RAW_SELL_TRADE)
        assert t.type == TradeType.SELL
        assert t.leverage is None
        assert t.bonus_portion == pytest.approx(0.794391178)

    def test_short_open(self):
        t = Trade.from_raw(RAW_SHORT_OPEN)
        assert t.type == TradeType.SHORT_OPEN
        assert t.qty == 0  # Shorts: qty is always 0
        assert t.leverage is None  # No leverage on shorts


# ---------------------------------------------------------------------------
# GameHistoryRecord
# ---------------------------------------------------------------------------


class TestGameHistoryRecord:
    def test_from_raw(self):
        rec = GameHistoryRecord.from_raw(RAW_GAME_HISTORY_ENTRY)
        assert rec.id == "20260206-74fb8b07116b4d39"
        assert rec.timestamp == 1770347058350
        assert rec.peak_multiplier == pytest.approx(7.07)
        assert rec.rugged is True
        assert rec.game_version == "v3"
        assert len(rec.prices) == 4
        assert rec.prices[0] == 1.0
        # globalTrades is always empty on public feed
        assert rec.global_trades == []
        assert len(rec.global_sidebets) == 1
        assert rec.global_sidebets[0].type == "placed"
        assert rec.global_sidebets[0].bet_amount == 0.002
        # Provably fair revealed
        assert rec.provably_fair.server_seed.endswith("dead")
        assert rec.provably_fair.server_seed_hash == "c1709d66abcdef"

    def test_null_global_trades(self):
        """globalTrades is ALWAYS null on public feed - must handle gracefully."""
        raw = {**RAW_GAME_HISTORY_ENTRY, "globalTrades": None}
        rec = GameHistoryRecord.from_raw(raw)
        assert rec.global_trades == []


# ---------------------------------------------------------------------------
# DailyRecords
# ---------------------------------------------------------------------------


class TestDailyRecords:
    def test_no_god_candle(self):
        data = {
            "highestToday": 55.3,
            "highestTodayTimestamp": 123456,
        }
        dr = DailyRecords.from_raw(data)
        assert dr.highest_today == pytest.approx(55.3)
        assert dr.has_god_candle is False

    def test_with_god_candle(self):
        data = {
            "highestToday": 1122.278,
            "godCandle2x": 15.5,
            "godCandle2xTimestamp": 999,
            "godCandle2xGameId": "game1",
            "godCandle2xServerSeed": "seed1",
            "godCandle2xMassiveJump": [10.0, 15.5],
        }
        dr = DailyRecords.from_raw(data)
        assert dr.has_god_candle is True
        assert dr.god_candle_2x.multiplier == 15.5
        assert dr.god_candle_2x.massive_jump == [10.0, 15.5]

    def test_god_candle_game_ids_single_tier(self):
        data = {
            "highestToday": 1122.278,
            "godCandle2x": 15.5,
            "godCandle2xGameId": "gc-game-A",
        }
        dr = DailyRecords.from_raw(data)
        assert dr.god_candle_game_ids == {"gc-game-A"}

    def test_god_candle_game_ids_multi_tier(self):
        data = {
            "highestToday": 1500.0,
            "godCandle2x": 15.5,
            "godCandle2xGameId": "gc-2x",
            "godCandle50x": 1122.278,
            "godCandle50xGameId": "gc-50x",
        }
        dr = DailyRecords.from_raw(data)
        assert dr.god_candle_game_ids == {"gc-2x", "gc-50x"}

    def test_god_candle_game_ids_empty_when_no_gc(self):
        data = {"highestToday": 55.3}
        dr = DailyRecords.from_raw(data)
        assert dr.god_candle_game_ids == set()


# ---------------------------------------------------------------------------
# SanitizedEvent
# ---------------------------------------------------------------------------


class TestSanitizedEvent:
    def test_create(self):
        stats = SessionStats(connected_players=150)
        evt = SanitizedEvent.create(
            channel=Channel.STATS,
            event_type="gameStateUpdate",
            model=stats,
            game_id="20260206-test",
            phase=Phase.ACTIVE,
        )
        assert evt.channel == Channel.STATS
        assert evt.event_type == "gameStateUpdate"
        assert evt.game_id == "20260206-test"
        assert evt.phase == Phase.ACTIVE
        assert evt.data["connected_players"] == 150
        assert "T" in evt.timestamp  # ISO format
