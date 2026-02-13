"""Tests for the core sanitization pipeline."""

import json

import pytest
from src.models import Channel, Phase, SanitizedEvent
from src.sanitizer import SanitizationPipeline

# ---------------------------------------------------------------------------
# Reference raw messages (as they come from rugs-feed broadcaster)
# ---------------------------------------------------------------------------


def make_raw_event(event_type: str, data: dict, game_id: str = "") -> dict:
    """Create a raw rugs-feed message envelope."""
    return {
        "type": "raw_event",
        "event_type": event_type,
        "data": data,
        "timestamp": "2026-02-06T03:04:19.123456",
        "game_id": game_id or data.get("gameId", ""),
    }


ACTIVE_DATA = {
    "gameId": "20260206-testgame",
    "active": True,
    "rugged": False,
    "price": 1.5,
    "tickCount": 50,
    "tradeCount": 30,
    "cooldownTimer": 0,
    "cooldownPaused": False,
    "allowPreRoundBuys": False,
    "connectedPlayers": 172,
    "averageMultiplier": 15.037,
    "count2x": 52,
    "count10x": 9,
    "count50x": 1,
    "count100x": 1,
    "provablyFair": {"serverSeedHash": "abc123", "version": "v3"},
    "leaderboard": [],
}

RUGGED_DATA = {
    "gameId": "20260206-testgame",
    "active": True,
    "rugged": True,
    "price": 0.001784,
    "tickCount": 255,
    "cooldownTimer": 0,
    "connectedPlayers": 170,
    "provablyFair": {
        "serverSeedHash": "abc123",
        "serverSeed": "revealed_seed",
        "version": "v3",
    },
    "leaderboard": [],
}

TRADE_DATA = {
    "id": "trade-uuid-1",
    "gameId": "20260206-testgame",
    "playerId": "did:privy:test1",
    "username": "TestPlayer",
    "level": 20,
    "price": 1.5,
    "type": "buy",
    "tickIndex": 50,
    "coin": "solana",
    "amount": 0.1,
    "qty": 0.0667,
    "leverage": 2,
    "bonusPortion": 0,
    "realPortion": 0.1,
}

HISTORY_DATA = {
    **ACTIVE_DATA,
    "gameHistory": [
        {
            "id": "20260206-history1",
            "timestamp": 1770347058350,
            "peakMultiplier": 3.5,
            "rugged": True,
            "gameVersion": "v3",
            "prices": [1.0, 1.05, 0.95],
            "globalTrades": None,
            "globalSidebets": [],
            "provablyFair": {
                "serverSeed": "seed1",
                "serverSeedHash": "hash1",
            },
        },
        {
            "id": "20260206-history2",
            "timestamp": 1770347058400,
            "peakMultiplier": 7.0,
            "rugged": True,
            "gameVersion": "v3",
            "prices": [1.0, 2.0, 7.0, 0.01],
            "globalTrades": None,
            "globalSidebets": [],
            "provablyFair": {
                "serverSeed": "seed2",
                "serverSeedHash": "hash2",
            },
        },
    ],
}


# ---------------------------------------------------------------------------
# Pipeline: gameStateUpdate processing
# ---------------------------------------------------------------------------


class TestGameStateProcessing:
    def setup_method(self):
        self.pipeline = SanitizationPipeline()

    def test_active_tick_produces_game_and_stats(self):
        raw = make_raw_event("gameStateUpdate", ACTIVE_DATA)
        events = self.pipeline.process_raw(raw)
        # Should produce at least 2 events: game + stats
        assert len(events) >= 2
        channels = [e.channel for e in events]
        assert Channel.GAME in channels
        assert Channel.STATS in channels

    def test_game_event_has_phase(self):
        raw = make_raw_event("gameStateUpdate", ACTIVE_DATA)
        events = self.pipeline.process_raw(raw)
        game_evt = next(e for e in events if e.channel == Channel.GAME)
        assert game_evt.phase == Phase.ACTIVE
        assert game_evt.game_id == "20260206-testgame"

    def test_stats_event_has_connected_players(self):
        raw = make_raw_event("gameStateUpdate", ACTIVE_DATA)
        events = self.pipeline.process_raw(raw)
        stats_evt = next(e for e in events if e.channel == Channel.STATS)
        assert stats_evt.data["connected_players"] == 172
        assert stats_evt.data["average_multiplier"] == pytest.approx(15.037)

    def test_rugged_tick_phase(self):
        # First set up ACTIVE phase
        self.pipeline.process_raw(make_raw_event("gameStateUpdate", ACTIVE_DATA))
        # Now rug
        raw = make_raw_event("gameStateUpdate", RUGGED_DATA)
        events = self.pipeline.process_raw(raw)
        game_evt = next(e for e in events if e.channel == Channel.GAME)
        assert game_evt.phase == Phase.RUGGED

    def test_game_history_produces_history_events(self):
        raw = make_raw_event("gameStateUpdate", HISTORY_DATA)
        events = self.pipeline.process_raw(raw)
        history_events = [e for e in events if e.channel == Channel.HISTORY]
        assert len(history_events) == 2
        assert history_events[0].data["id"] == "20260206-history1"
        assert history_events[1].data["id"] == "20260206-history2"

    def test_god_candle_flag_propagates(self):
        data = {
            **ACTIVE_DATA,
            "highestToday": 1122.0,
            "godCandle2x": 15.5,
            "godCandle2xTimestamp": 999,
            "godCandle2xGameId": "gc-game",
            "godCandle2xServerSeed": "gc-seed",
            "godCandle2xMassiveJump": [10.0, 15.5],
        }
        raw = make_raw_event("gameStateUpdate", data)
        events = self.pipeline.process_raw(raw)
        game_evt = next(e for e in events if e.channel == Channel.GAME)
        assert game_evt.data["has_god_candle"] is True

    def test_stale_god_candle_not_reflagged(self):
        """Same god candle data repeated should be suppressed by GodCandleDetector."""
        data = {
            **ACTIVE_DATA,
            "highestToday": 1122.0,
            "godCandle2x": 15.5,
            "godCandle2xTimestamp": 999,
            "godCandle2xGameId": "gc-game",
            "godCandle2xServerSeed": "gc-seed",
        }
        raw = make_raw_event("gameStateUpdate", data)
        # First time: new god candle
        events1 = self.pipeline.process_raw(raw)
        game1 = next(e for e in events1 if e.channel == Channel.GAME)
        assert game1.data["has_god_candle"] is True

        # Second time: stale — same gc-game ID
        events2 = self.pipeline.process_raw(raw)
        game2 = next(e for e in events2 if e.channel == Channel.GAME)
        assert game2.data["has_god_candle"] is False


# ---------------------------------------------------------------------------
# Pipeline: trade processing
# ---------------------------------------------------------------------------


class TestTradeProcessing:
    def setup_method(self):
        self.pipeline = SanitizationPipeline()
        # Set phase to ACTIVE first
        self.pipeline.process_raw(make_raw_event("gameStateUpdate", ACTIVE_DATA))

    def test_trade_produces_trade_event(self):
        raw = make_raw_event("standard/newTrade", TRADE_DATA)
        events = self.pipeline.process_raw(raw)
        assert len(events) == 1
        assert events[0].channel == Channel.TRADES
        assert events[0].event_type == "standard/newTrade"

    def test_trade_annotations(self):
        raw = make_raw_event("standard/newTrade", TRADE_DATA)
        events = self.pipeline.process_raw(raw)
        trade_data = events[0].data
        assert trade_data["token_type"] == "real"
        assert trade_data["is_practice"] is False
        assert trade_data["is_forced_sell"] is False

    def test_forced_sell_during_rug(self):
        # First rug the game
        self.pipeline.process_raw(make_raw_event("gameStateUpdate", RUGGED_DATA))
        # Then a sell trade
        sell_data = {**TRADE_DATA, "type": "sell", "price": 0.001784}
        raw = make_raw_event("standard/newTrade", sell_data)
        events = self.pipeline.process_raw(raw)
        assert events[0].data["is_forced_sell"] is True

    def test_practice_trade_annotation(self):
        trade_data = {
            **TRADE_DATA,
            "bonusPortion": 0.1,
            "realPortion": 0,
        }
        raw = make_raw_event("standard/newTrade", trade_data)
        events = self.pipeline.process_raw(raw)
        assert events[0].data["is_practice"] is True
        assert events[0].data["token_type"] == "practice"


# ---------------------------------------------------------------------------
# Pipeline: callbacks
# ---------------------------------------------------------------------------


class TestCallbacks:
    def setup_method(self):
        self.pipeline = SanitizationPipeline()
        self.game_events: list[SanitizedEvent] = []
        self.stats_events: list[SanitizedEvent] = []
        self.all_events: list[SanitizedEvent] = []

        self.pipeline.on_event(Channel.GAME, self.game_events.append)
        self.pipeline.on_event(Channel.STATS, self.stats_events.append)
        self.pipeline.on_event(Channel.ALL, self.all_events.append)

    def test_callbacks_receive_events(self):
        raw = make_raw_event("gameStateUpdate", ACTIVE_DATA)
        self.pipeline.process_raw(raw)
        assert len(self.game_events) == 1
        assert len(self.stats_events) == 1
        # ALL gets both game + stats
        assert len(self.all_events) == 2

    def test_trade_callback_separate(self):
        trade_events: list[SanitizedEvent] = []
        self.pipeline.on_event(Channel.TRADES, trade_events.append)

        # Process a game state first (to set phase)
        self.pipeline.process_raw(make_raw_event("gameStateUpdate", ACTIVE_DATA))
        # Then a trade
        self.pipeline.process_raw(make_raw_event("standard/newTrade", TRADE_DATA))
        assert len(trade_events) == 1
        # ALL also gets it
        assert len(self.all_events) == 3  # 2 from game state + 1 from trade


# ---------------------------------------------------------------------------
# Pipeline: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def setup_method(self):
        self.pipeline = SanitizationPipeline()

    def test_json_string_input(self):
        raw = json.dumps(make_raw_event("gameStateUpdate", ACTIVE_DATA))
        events = self.pipeline.process_raw(raw)
        assert len(events) >= 2

    def test_invalid_json(self):
        events = self.pipeline.process_raw("not json at all")
        assert events == []

    def test_empty_data(self):
        """Empty data dict is falsy — pipeline skips it."""
        events = self.pipeline.process_raw({"event_type": "gameStateUpdate", "data": {}})
        assert events == []

    def test_unknown_event_type(self):
        raw = make_raw_event("unknownEvent", {"foo": "bar"})
        events = self.pipeline.process_raw(raw)
        assert events == []

    def test_missing_event_type(self):
        events = self.pipeline.process_raw({"data": {"foo": "bar"}})
        assert events == []

    def test_stats_tracking(self):
        self.pipeline.process_raw(make_raw_event("gameStateUpdate", ACTIVE_DATA))
        self.pipeline.process_raw(make_raw_event("standard/newTrade", TRADE_DATA))
        self.pipeline.process_raw("bad json")

        stats = self.pipeline.get_stats()
        assert stats["events_received"] == 2
        assert stats["game_events"] == 1
        assert stats["stats_events"] == 1
        assert stats["trade_events"] == 1
        assert stats["parse_errors"] == 1
