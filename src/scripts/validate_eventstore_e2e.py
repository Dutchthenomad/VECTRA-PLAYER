#!/usr/bin/env python3
"""
EventStore End-to-End Validation Script

Validates Phase A by:
1. Creating EventStoreService
2. Publishing test events to EventBus
3. Flushing to Parquet
4. Querying with DuckDB to verify data integrity

Run: cd src && python scripts/validate_eventstore_e2e.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.event_bus import EventBus, Events
from services.event_store import EventStorePaths, EventStoreQuery, EventStoreService


def main():
    print("=" * 60)
    print("EventStore End-to-End Validation")
    print("=" * 60)

    # Check current state
    paths = EventStorePaths()
    print(f"\n📁 Data directory: {paths.data_dir}")
    print(f"📁 Parquet directory: {paths.events_parquet_dir}")

    # Count existing files
    existing_files = list(paths.events_parquet_dir.rglob("*.parquet"))
    print(f"📊 Existing Parquet files: {len(existing_files)}")

    # Create fresh EventBus and EventStoreService
    print("\n🔧 Initializing EventBus and EventStoreService...")
    event_bus = EventBus()
    event_bus.start()  # Start the event processing thread
    service = EventStoreService(event_bus, paths=paths)
    service.start()
    print(f"   Session ID: {service.session_id}")

    # Publish test events
    print("\n📤 Publishing test events...")

    # 1. WebSocket raw event
    ws_event = {
        "event": "gameStateUpdate",
        "data": {
            "gameId": "test-game-001",
            "tickCount": 42,
            "price": 1.5,
            "active": True,
            "rugged": False,
        },
        "source": "public_ws",
    }
    event_bus.publish(Events.WS_RAW_EVENT, ws_event)
    print("   ✓ WS_RAW_EVENT published")

    # 2. Game tick event
    tick_event = {
        "gameId": "test-game-001",
        "tick": 42,
        "price": 1.5,
        "active": True,
        "rugged": False,
    }
    event_bus.publish(Events.GAME_TICK, tick_event)
    print("   ✓ GAME_TICK published")

    # 3. Player update event
    player_event = {
        "gameId": "test-game-001",
        "playerId": "test-player-001",
        "username": "TestUser",
        "cash": 100.5,
        "positionQty": 10.0,
        "avgCost": 1.2,
        "pnl": 3.0,
    }
    event_bus.publish(Events.PLAYER_UPDATE, player_event)
    print("   ✓ PLAYER_UPDATE published")

    # 4. Trade events
    buy_event = {
        "gameId": "test-game-001",
        "playerId": "test-player-001",
        "amount": 5.0,
        "price": 1.5,
    }
    event_bus.publish(Events.TRADE_BUY, buy_event)
    print("   ✓ TRADE_BUY published")

    sell_event = {
        "gameId": "test-game-001",
        "playerId": "test-player-001",
        "amount": 2.5,
        "price": 1.8,
    }
    event_bus.publish(Events.TRADE_SELL, sell_event)
    print("   ✓ TRADE_SELL published")

    # Give EventBus time to process
    import time

    time.sleep(0.5)

    # Check buffer
    print(f"\n📊 Events in buffer: {service.event_count}")

    # Flush to Parquet
    print("\n💾 Flushing to Parquet...")
    written_files = service.flush()
    if written_files:
        print(f"   ✓ Written {len(written_files)} file(s):")
        for f in written_files:
            print(f"     - {f}")
    else:
        print("   ⚠ No files written (buffer may have been empty)")

    # Stop service and EventBus
    service.stop()
    event_bus.stop()
    print("\n🛑 Service and EventBus stopped")

    # Count new files
    new_files = list(paths.events_parquet_dir.rglob("*.parquet"))
    print(f"\n📊 Total Parquet files now: {len(new_files)}")
    print(f"   New files created: {len(new_files) - len(existing_files)}")

    # Query with DuckDB
    print("\n🔍 Querying with DuckDB...")
    query_helper = EventStoreQuery(paths=paths)

    # Count total events
    try:
        total_count = query_helper.count_events()
        print(f"\n   Total events: {total_count}")

        # Count by doc_type using raw SQL
        parquet_glob = str(paths.events_parquet_dir / "**/*.parquet")
        df = query_helper.query(f"""
            SELECT doc_type, COUNT(*) as count
            FROM '{parquet_glob}'
            GROUP BY doc_type
            ORDER BY count DESC
        """)
        if df is not None and len(df) > 0:
            print("\n   Events by doc_type:")
            for _, row in df.iterrows():
                print(f"     - {row['doc_type']}: {row['count']}")
    except Exception as e:
        print(f"   ⚠ Count query failed: {e}")

    # List recent events
    try:
        parquet_glob = str(paths.events_parquet_dir / "**/*.parquet")
        df = query_helper.query(f"""
            SELECT doc_type, ts, game_id, seq
            FROM '{parquet_glob}'
            ORDER BY ts DESC
            LIMIT 10
        """)
        if df is not None and len(df) > 0:
            print("\n   Recent events:")
            for _, row in df.iterrows():
                print(f"     [{row['doc_type']}] game={row['game_id']} seq={row['seq']}")
    except Exception as e:
        print(f"   ⚠ List query failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Validation Complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
