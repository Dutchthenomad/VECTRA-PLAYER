#!/usr/bin/env python3
"""
Convert captured WebSocket events to Parquet format.
Tests the EventStore schema with real live data.

Run: cd src && python scripts/convert_captured_to_parquet.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.event_store import (
    Direction,
    DocType,
    EventEnvelope,
    EventSource,
    EventStorePaths,
    ParquetWriter,
)


def extract_events_from_mcp_output(file_path: Path) -> list[dict]:
    """Extract events from MCP tool output file."""
    content = file_path.read_text()

    # Find the JSON array in the markdown code block
    match = re.search(r'```json\s*"(\[.*\])"\s*```', content, re.DOTALL)
    if not match:
        # Try without escaped quotes
        match = re.search(r"```json\s*(\[.*\])\s*```", content, re.DOTALL)

    if match:
        json_str = match.group(1)
        # Unescape if needed
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1]
        # Replace escaped quotes
        json_str = json_str.replace('\\"', '"').replace("\\n", "\n")
        return json.loads(json_str)

    # Try parsing as plain JSON array
    try:
        data = json.loads(content)
        if isinstance(data, list) and len(data) > 0 and "text" in data[0]:
            # MCP format: [{type: text, text: "..."}]
            text = data[0]["text"]
            match = re.search(r'```json\s*"(.+?)"\s*```', text, re.DOTALL)
            if match:
                json_str = match.group(1).replace('\\"', '"').replace("\\n", "\n")
                return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return []


def main():
    print("=" * 60)
    print("Convert Captured Events to Parquet")
    print("=" * 60)

    # Find the captured file
    captured_file = Path.home() / "rugs_data" / "captured_events_raw.json"
    if not captured_file.exists():
        print(f"Error: {captured_file} not found")
        return 1

    print(f"\n📁 Reading: {captured_file}")
    print(f"   File size: {captured_file.stat().st_size:,} bytes")

    # Extract events
    events = extract_events_from_mcp_output(captured_file)
    print(f"\n📊 Extracted {len(events)} events")

    if not events:
        print("   No events found in file")
        return 1

    # Show sample event
    print("\n📋 Sample event:")
    sample = events[0]
    print(f"   Event: {sample.get('event')}")
    print(f"   Timestamp: {sample.get('timestamp')}")
    if "data" in sample:
        data = sample["data"]
        print(f"   Game ID: {data.get('gameId')}")
        print(f"   Tick: {data.get('tickCount')}")
        print(f"   Price: {data.get('price')}")

    # Initialize ParquetWriter
    paths = EventStorePaths()
    writer = ParquetWriter(paths=paths, buffer_size=200)
    session_id = "cdp-capture-" + datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n🔧 Writing to: {paths.events_parquet_dir}")
    print(f"   Session ID: {session_id}")

    # Convert events to EventEnvelope format
    from decimal import Decimal

    for i, event in enumerate(events):
        ts_ms = event.get("timestamp", 0)
        ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        data = event.get("data", {})

        # Create EventEnvelope
        envelope = EventEnvelope(
            ts=ts,
            source=EventSource.CDP,
            doc_type=DocType.WS_EVENT,
            session_id=session_id,
            game_id=data.get("gameId"),
            player_id=None,
            username=None,
            seq=i,
            direction=Direction.RECEIVED,
            raw_json=json.dumps(event),
            # Type-specific fields
            event_name=event.get("event", "gameStateUpdate"),
            tick=data.get("tickCount"),
            price=Decimal(str(data.get("price"))) if data.get("price") else None,
        )
        writer.write(envelope)

    print(f"\n💾 Flushing {len(events)} events to Parquet...")
    written_files = writer.flush()

    if written_files:
        print(f"   ✓ Written {len(written_files)} file(s):")
        for f in written_files:
            print(f"     - {f}")
    else:
        print("   ⚠ No files written")

    print("\n" + "=" * 60)
    print("✅ Conversion Complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
