"""
Tests for complete game capture from gameHistory

Validates that complete games from gameStateUpdate.gameHistory
are captured with ALL fields preserved in Parquet.
"""

import json

import duckdb

from services.event_bus import EventBus, Events
from services.event_store.paths import EventStorePaths
from services.event_store.schema import DocType
from services.event_store.service import EventStoreService


class TestCompleteGameCapture:
    """Test complete game capture from gameHistory array"""

    def test_complete_game_doctype_exists(self):
        """COMPLETE_GAME DocType should exist"""
        assert DocType.COMPLETE_GAME == "complete_game"

    def test_capture_gamehistory_from_gameStateUpdate(self, tmp_path):
        """Should capture complete games when gameStateUpdate has gameHistory"""
        # Setup
        event_bus = EventBus()
        event_bus.start()
        paths = EventStorePaths(data_dir=tmp_path)
        service = EventStoreService(event_bus, paths=paths)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        # Simulate gameStateUpdate with gameHistory (rug event)
        rug_event = {
            "data": {
                "event": "gameStateUpdate",
                "data": {
                    "gameId": "current_live_game",
                    "price": 1.5,
                    "tickCount": 50,
                    "gameHistory": [
                        {
                            "id": "game_1",
                            "timestamp": 1767505016696,
                            "gameVersion": "v3",
                            "rugged": True,
                            "peakMultiplier": 8.33,
                            "globalSidebets": [
                                {
                                    "playerId": "player_1",
                                    "username": "test_player",
                                    "betAmount": 0.1,
                                    "xPayout": 5,
                                    "startedAtTick": 10,
                                    "end": 50,
                                },
                                {
                                    "playerId": "player_2",
                                    "username": "test_player_2",
                                    "betAmount": 0.05,
                                    "xPayout": 10,
                                    "startedAtTick": 20,
                                    "end": 60,
                                },
                            ],
                            "prices": [1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 8.33],
                            "provablyFair": {
                                "serverSeed": "test_seed",
                                "serverSeedHash": "test_hash",
                            },
                        },
                        {
                            "id": "game_2",
                            "timestamp": 1767505056789,
                            "gameVersion": "v3",
                            "rugged": True,
                            "peakMultiplier": 2.4,
                            "globalSidebets": [],
                            "prices": [1.0, 1.2, 1.5, 2.0, 2.4],
                            "provablyFair": {
                                "serverSeed": "test_seed_2",
                                "serverSeedHash": "test_hash_2",
                            },
                        },
                    ],
                },
            }
        }

        # Publish event
        event_bus.publish(Events.WS_RAW_EVENT, rug_event)

        # Wait for EventBus processing
        import time

        time.sleep(0.3)

        # Flush to Parquet
        service.flush()
        service.stop()
        event_bus.stop()

        # Verify Parquet files were created
        game_files = list(paths.events_parquet_dir.glob("doc_type=complete_game/**/*.parquet"))
        assert len(game_files) > 0, "No complete_game Parquet files created"

        # Read and verify content
        conn = duckdb.connect()
        df = conn.execute(f"""
            SELECT game_id, raw_json
            FROM read_parquet('{game_files[0]}')
        """).df()

        # Should have 2 complete games
        assert len(df) == 2

        # Verify game 1 is complete with ALL fields
        game1_json = json.loads(df[df["game_id"] == "game_1"]["raw_json"].iloc[0])
        assert game1_json["id"] == "game_1"
        assert game1_json["peakMultiplier"] == 8.33
        assert game1_json["rugged"] is True

        # Verify globalSidebets are preserved COMPLETELY
        assert "globalSidebets" in game1_json
        assert len(game1_json["globalSidebets"]) == 2
        assert game1_json["globalSidebets"][0]["username"] == "test_player"
        assert game1_json["globalSidebets"][0]["betAmount"] == 0.1
        assert game1_json["globalSidebets"][0]["xPayout"] == 5

        # Verify prices array is preserved COMPLETELY
        assert "prices" in game1_json
        assert len(game1_json["prices"]) == 8
        assert game1_json["prices"][0] == 1.0
        assert game1_json["prices"][-1] == 8.33

        # Verify provablyFair is preserved
        assert "provablyFair" in game1_json
        assert game1_json["provablyFair"]["serverSeed"] == "test_seed"

        # Verify game 2 (no sidebets)
        game2_json = json.loads(df[df["game_id"] == "game_2"]["raw_json"].iloc[0])
        assert game2_json["id"] == "game_2"
        assert len(game2_json["globalSidebets"]) == 0
        assert len(game2_json["prices"]) == 5

    def test_skip_gameStateUpdate_without_gameHistory(self, tmp_path):
        """Should not create complete_game events for normal gameStateUpdate"""
        # Setup
        event_bus = EventBus()
        event_bus.start()
        paths = EventStorePaths(data_dir=tmp_path)
        service = EventStoreService(event_bus, paths=paths)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        # Normal gameStateUpdate (no gameHistory)
        normal_event = {
            "data": {
                "event": "gameStateUpdate",
                "data": {
                    "gameId": "active_game",
                    "price": 2.5,
                    "tickCount": 100,
                    "active": True,
                    # No gameHistory field
                },
            }
        }

        event_bus.publish(Events.WS_RAW_EVENT, normal_event)

        # Wait for EventBus processing
        import time

        time.sleep(0.3)

        service.flush()
        service.stop()
        event_bus.stop()

        # Should NOT create complete_game files
        game_files = list(paths.events_parquet_dir.glob("doc_type=complete_game/**/*.parquet"))
        assert len(game_files) == 0

    def test_deduplicate_rug_emissions(self, tmp_path):
        """Should deduplicate games from duplicate rug event emissions"""
        # Setup
        event_bus = EventBus()
        event_bus.start()
        paths = EventStorePaths(data_dir=tmp_path)
        service = EventStoreService(event_bus, paths=paths)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        # First emission (emission 1 of rug pair)
        emission1 = {
            "data": {
                "event": "gameStateUpdate",
                "data": {
                    "gameId": "current_game",
                    "gameHistory": [
                        {"id": "game_1", "timestamp": 1767505016696, "prices": [1.0, 2.0]},
                    ],
                },
            }
        }

        # Second emission ~500ms later (emission 2 of rug pair - duplicate)
        emission2 = {
            "data": {
                "event": "gameStateUpdate",
                "data": {
                    "gameId": "current_game",
                    "gameHistory": [
                        {"id": "game_1", "timestamp": 1767505016696, "prices": [1.0, 2.0]},
                    ],
                },
            }
        }

        event_bus.publish(Events.WS_RAW_EVENT, emission1)
        event_bus.publish(Events.WS_RAW_EVENT, emission2)

        # Wait for EventBus processing
        import time

        time.sleep(0.3)

        service.flush()
        service.stop()
        event_bus.stop()

        # With deduplication, same game_id should only be captured ONCE
        game_files = list(paths.events_parquet_dir.glob("doc_type=complete_game/**/*.parquet"))
        assert len(game_files) > 0

        conn = duckdb.connect()
        df = conn.execute(f"""
            SELECT COUNT(*) as count
            FROM read_parquet('{game_files[0]}')
        """).df()

        # Deduplication: Only 1 record for the same game_id
        assert df["count"].iloc[0] == 1
