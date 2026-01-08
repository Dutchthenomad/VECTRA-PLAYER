"""
Integration test for CDP WebSocket -> EventBus -> EventStore pipeline.

This test verifies the fix for the double-unwrapping bug where:
- EventBus wraps events as: {"name": event_type, "data": payload}
- BrowserBridge wraps CDP events as: {"data": cdp_event}
- EventStoreService must unwrap both layers to access the CDP event
"""

import tempfile
import time
from pathlib import Path

import duckdb

from services.event_bus import EventBus, Events
from services.event_store.paths import EventStorePaths
from services.event_store.service import EventStoreService
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor


class TestCDPEventStoreIntegration:
    """Test CDP capture pipeline end-to-end"""

    def test_cdp_to_parquet_pipeline(self):
        """CDP events flow through EventBus and are persisted to Parquet"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create pipeline components
            test_event_bus = EventBus()
            test_event_bus.start()

            paths = EventStorePaths(data_dir=temp_path)
            paths.ensure_directories()

            event_store = EventStoreService(
                event_bus=test_event_bus, paths=paths, session_id="test-cdp-pipeline"
            )
            event_store.start()
            event_store.resume()  # Enable recording (EventStore starts paused by default)

            # Create CDP interceptor and wire it like BrowserBridge does
            interceptor = CDPWebSocketInterceptor()
            interceptor.on_event = lambda e: test_event_bus.publish(
                Events.WS_RAW_EVENT, {"data": e}
            )
            interceptor.rugs_websocket_id = "test-ws"

            # Send test frames
            test_frames = [
                {
                    "requestId": "test-ws",
                    "timestamp": 1734567890.0,
                    "response": {
                        "payloadData": '42["gameStateUpdate",{"gameId":"game123","price":2.5,"tick":100}]'
                    },
                },
                {
                    "requestId": "test-ws",
                    "timestamp": 1734567891.0,
                    "response": {"payloadData": '42["usernameStatus",{"username":"TestUser"}]'},
                },
                {
                    "requestId": "test-ws",
                    "timestamp": 1734567892.0,
                    "response": {
                        "payloadData": '42["playerUpdate",{"gameId":"game123","cash":10.5}]'
                    },
                },
            ]

            for frame in test_frames:
                interceptor._handle_frame_received(frame)

            # Wait for async processing
            time.sleep(1.0)

            # Flush and stop
            event_store.flush()
            event_store.stop()
            test_event_bus.stop()

            # Verify Parquet files created
            parquet_files = list(paths.events_parquet_dir.rglob("*.parquet"))
            assert len(parquet_files) > 0, "No Parquet files created"

            # Verify data using DuckDB
            conn = duckdb.connect()
            df = conn.execute(
                f"SELECT event_name, game_id, doc_type, source, seq FROM '{parquet_files[0]}' ORDER BY seq"
            ).df()

            # Verify 3 events captured
            assert len(df) == 3

            # Verify event names (tests double unwrapping)
            events = df["event_name"].tolist()
            assert "gameStateUpdate" in events
            assert "usernameStatus" in events
            assert "playerUpdate" in events

            # Verify game_id extraction
            assert df.iloc[0]["game_id"] == "game123"
            assert df.iloc[2]["game_id"] == "game123"

            # Verify metadata
            assert all(df["doc_type"] == "ws_event")
            assert all(df["source"] == "public_ws")
            assert list(df["seq"]) == [1, 2, 3]

    def test_cdp_interceptor_stats(self):
        """CDP interceptor tracks received events correctly"""
        interceptor = CDPWebSocketInterceptor()
        interceptor.rugs_websocket_id = "test-ws"

        # Simulate receiving a frame
        interceptor._handle_frame_received(
            {
                "requestId": "test-ws",
                "timestamp": 1234567890.0,
                "response": {"payloadData": '42["gameStateUpdate",{"price":1.5}]'},
            }
        )

        stats = interceptor.get_stats()
        assert stats["events_received"] == 1
        assert stats["has_rugs_websocket"] is True
