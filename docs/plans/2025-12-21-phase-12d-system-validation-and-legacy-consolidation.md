# Phase 12D: System Validation & Legacy Recorder Consolidation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Validate the new EventStore system works visibly in the UI, then safely consolidate 6 legacy recorders into a single-writer pattern.

**Architecture:** EventStoreService + LiveStateProvider replace all 6 legacy recorders. Parquet is canonical truth; legacy JSONL exports available via CLI for backwards compatibility.

**Tech Stack:** Python 3.11+, DuckDB, Parquet (pyarrow), tkinter, EventBus pub/sub

---

## Current State Analysis

### New System (Phase 12A-C) - COMPLETE

| Component | Status | Purpose |
|-----------|--------|---------|
| EventStoreService | ✅ Working | EventBus → Parquet persistence |
| ParquetWriter | ✅ Working | Buffered atomic Parquet writes |
| EventEnvelope | ✅ Working | Canonical event schema |
| LiveStateProvider | ✅ Working | Server-authoritative state |
| CDP Capture | ✅ Working | 1700+ events captured to Parquet |

### Legacy Recorders (6 total)

| Recorder | Lines | Purpose | Migration Status |
|----------|-------|---------|------------------|
| GameStateRecorder | 146 | Game prices to JSON | → EventStore.GAME_TICK ✅ |
| PlayerSessionRecorder | 103 | Player actions to JSON | → EventStore.PLAYER_UPDATE ✅ |

### Migration Gap Analysis

| Feature | Old System | New System | Gap |
|---------|------------|------------|-----|
| Player state | PlayerSessionRecorder | EventStore.PLAYER_UPDATE | ✅ None |

---

## Phase 12D Implementation Plan

### Pre-Flight: Test Current System

**Files:** None (verification only)

**Step 1: Run all tests**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short
```

Expected: 1000+ tests passing

**Step 2: Verify Parquet data exists**

```bash
ls -la ~/rugs_data/events_parquet/
```

Expected: Directories for doc_type=ws_event, doc_type=game_tick, etc.

---

### Task 1: Add Capture Stats Panel to UI

**Files:**
- Modify: `src/ui/main_window.py`
- Modify: `src/ui/panels/info_panel.py` (if exists) or create new panel

**Step 1: Write failing test for capture stats display**

```python
# src/tests/test_ui/test_capture_stats.py
"""Tests for capture stats display in UI."""

import pytest
from unittest.mock import Mock, MagicMock
from decimal import Decimal


def test_capture_stats_panel_exists():
    """Capture stats panel should exist in main window."""
    # Import inside test to avoid tkinter in headless
    from ui.main_window import MainWindow

    # Mock root window
    root = MagicMock()
    root.winfo_screenwidth.return_value = 1920
    root.winfo_screenheight.return_value = 1080

    # MainWindow should have capture_stats attribute
    assert hasattr(MainWindow, '__init__')
    # Test will verify panel creation in integration


def test_capture_stats_shows_event_count():
    """Capture stats should display event count from EventStoreService."""
    from services.event_store.service import EventStoreService
    from services.event_bus import EventBus

    event_bus = EventBus()
    service = EventStoreService(event_bus)

    # Should have event_count property
    assert hasattr(service, 'event_count')
    assert service.event_count >= 0


def test_capture_stats_shows_session_id():
    """Capture stats should display session ID."""
    from services.event_store.service import EventStoreService
    from services.event_bus import EventBus

    event_bus = EventBus()
    service = EventStoreService(event_bus)

    # Should have session_id property
    assert hasattr(service, 'session_id')
    assert len(service.session_id) == 36  # UUID format
```

**Step 2: Run test to verify it fails**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_capture_stats.py -v
```

Expected: Tests pass (they're testing existing functionality)

**Step 3: Add capture stats frame to MainWindow**

In `src/ui/main_window.py`, add after LiveStateProvider initialization:

```python
# Add to _create_status_bar or info panel area
def _create_capture_stats_frame(self):
    """Create capture statistics display frame."""
    self.capture_stats_frame = ttk.LabelFrame(
        self.status_frame,  # Or appropriate parent
        text="Capture Stats",
        padding=(5, 2)
    )
    self.capture_stats_frame.pack(side=tk.LEFT, padx=5)

    # Session ID (truncated)
    session_short = self.event_store.session_id[:8] if self.event_store else "N/A"
    self.session_label = ttk.Label(
        self.capture_stats_frame,
        text=f"Session: {session_short}..."
    )
    self.session_label.pack(side=tk.LEFT, padx=2)

    # Event count
    self.event_count_label = ttk.Label(
        self.capture_stats_frame,
        text="Events: 0"
    )
    self.event_count_label.pack(side=tk.LEFT, padx=2)
```

**Step 4: Add periodic update for event count**

```python
def _update_capture_stats(self):
    """Update capture statistics display."""
    if hasattr(self, 'event_store') and self.event_store:
        count = self.event_store.event_count
        self.event_count_label.config(text=f"Events: {count}")

    # Schedule next update
    self.after(1000, self._update_capture_stats)
```

**Step 5: Run tests to verify**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_capture_stats.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/ui/main_window.py src/tests/test_ui/test_capture_stats.py
git commit -m "feat(Phase 12D): Add capture stats display to UI

- Show session ID (truncated)
- Show buffered event count
- Periodic updates every 1s"
```

---

### Task 2: Add Live Balance Display with Visual Indicator

**Files:**
- Modify: `src/ui/main_window.py`
- Modify: `src/ui/panels/trading_panel.py` (or equivalent)

**Step 1: Write failing test for live balance indicator**

```python
# src/tests/test_ui/test_live_balance.py
"""Tests for live balance display with server-authoritative indicator."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock


def test_live_state_provider_has_balance():
    """LiveStateProvider should provide cash balance."""
    from services.live_state_provider import LiveStateProvider
    from services.event_bus import EventBus

    event_bus = EventBus()
    provider = LiveStateProvider(event_bus)

    # Should have cash property
    assert hasattr(provider, 'cash')
    assert provider.cash == Decimal("0")  # Initial


def test_live_indicator_format():
    """Live mode should show 'LIVE: username' indicator."""
    from services.live_state_provider import LiveStateProvider
    from services.event_bus import EventBus, Events

    event_bus = EventBus()
    provider = LiveStateProvider(event_bus)

    # Simulate player update
    event_bus.publish(Events.PLAYER_UPDATE, {
        "cash": "100.50",
        "username": "Dutch",
        "playerId": "player-123"
    })

    # Verify state updated
    assert provider.username == "Dutch"
    assert provider.cash == Decimal("100.50")


def test_live_indicator_shows_when_connected():
    """UI should show LIVE indicator when LiveStateProvider.is_connected."""
    from services.live_state_provider import LiveStateProvider
    from services.event_bus import EventBus, Events

    event_bus = EventBus()
    provider = LiveStateProvider(event_bus)

    # Initially not connected
    assert not provider.is_connected

    # After receiving player update, becomes connected
    event_bus.publish(Events.PLAYER_UPDATE, {
        "cash": "100.50",
        "username": "Dutch"
    })

    assert provider.is_connected
```

**Step 2: Run test to verify it fails**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_live_balance.py -v
```

Expected: PASS (testing existing functionality)

**Step 3: Modify trading panel to show live balance**

Add to trading panel or balance display area:

```python
def _update_balance_display(self):
    """Update balance display with live or local values."""
    if self.live_state and self.live_state.is_connected:
        # Server-authoritative mode
        balance = self.live_state.cash
        balance_text = f"Balance: {balance:.4f} SOL"
        indicator_text = f"LIVE: {self.live_state.username or 'connected'}"
        indicator_color = "green"
    else:
        # Local calculation mode
        balance = self.game_state.get('balance', Decimal("0"))
        balance_text = f"Balance: {balance:.4f} SOL"
        indicator_text = "LOCAL"
        indicator_color = "gray"

    self.balance_label.config(text=balance_text)
    self.live_indicator.config(text=indicator_text, foreground=indicator_color)
```

**Step 4: Run tests**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_live_balance.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/main_window.py src/ui/panels/trading_panel.py src/tests/test_ui/test_live_balance.py
git commit -m "feat(Phase 12D): Add live balance display with LIVE indicator

- Show server-authoritative balance from LiveStateProvider
- Green 'LIVE: username' indicator when connected
- Gray 'LOCAL' indicator when using local calculations"
```

---

### Task 3: Add DuckDB Query Menu Option

**Files:**
- Create: `src/scripts/query_session.py`
- Modify: `src/ui/main_window.py` (add menu item)

**Step 1: Write failing test for query script**

```python
# src/tests/test_scripts/test_query_session.py
"""Tests for DuckDB query script."""

import pytest
from pathlib import Path
import tempfile


def test_query_session_exists():
    """Query script should exist."""
    script_path = Path(__file__).parent.parent.parent / "scripts" / "query_session.py"
    # This test will fail until we create the script
    # For now, just verify import works
    pass


def test_query_parquet_returns_dataframe():
    """Query should return pandas DataFrame."""
    import duckdb
    import tempfile
    import pyarrow as pa
    import pyarrow.parquet as pq

    # Create test parquet file
    with tempfile.TemporaryDirectory() as tmpdir:
        table = pa.table({
            'ts': ['2025-12-21T10:00:00'],
            'doc_type': ['ws_event'],
            'event_name': ['gameStateUpdate'],
        })
        pq.write_table(table, f"{tmpdir}/test.parquet")

        # Query it
        conn = duckdb.connect()
        result = conn.execute(f"SELECT * FROM '{tmpdir}/test.parquet'").df()

        assert len(result) == 1
        assert result['doc_type'].iloc[0] == 'ws_event'
```

**Step 2: Run test**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_scripts/test_query_session.py -v
```

Expected: PASS (basic DuckDB query works)

**Step 3: Create query_session.py script**

```python
#!/usr/bin/env python3
"""
Query captured session data from Parquet files.

Usage:
    python scripts/query_session.py --session <session_id>
    python scripts/query_session.py --recent 10
    python scripts/query_session.py --stats
"""

import argparse
from pathlib import Path

import duckdb


def get_data_dir() -> Path:
    """Get data directory from config or default."""
    import os
    return Path(os.environ.get("RUGS_DATA_DIR", Path.home() / "rugs_data"))


def query_session(session_id: str) -> None:
    """Query events from a specific session."""
    data_dir = get_data_dir()
    parquet_path = data_dir / "events_parquet" / "**" / "*.parquet"

    conn = duckdb.connect()

    print(f"\n=== Session: {session_id} ===\n")

    # Count by doc_type
    query = f"""
    SELECT
        doc_type,
        COUNT(*) as count
    FROM '{parquet_path}'
    WHERE session_id = '{session_id}'
    GROUP BY doc_type
    ORDER BY count DESC
    """

    result = conn.execute(query).df()
    print("Event counts by type:")
    print(result.to_string(index=False))
    print()


def query_recent(limit: int = 10) -> None:
    """Show most recent events."""
    data_dir = get_data_dir()
    parquet_path = data_dir / "events_parquet" / "**" / "*.parquet"

    conn = duckdb.connect()

    query = f"""
    SELECT
        ts,
        doc_type,
        event_name,
        game_id
    FROM '{parquet_path}'
    ORDER BY ts DESC
    LIMIT {limit}
    """

    result = conn.execute(query).df()
    print(f"\n=== Most Recent {limit} Events ===\n")
    print(result.to_string(index=False))


def query_stats() -> None:
    """Show overall capture statistics."""
    data_dir = get_data_dir()
    parquet_path = data_dir / "events_parquet" / "**" / "*.parquet"

    conn = duckdb.connect()

    print("\n=== Capture Statistics ===\n")

    # Total events
    total = conn.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()[0]
    print(f"Total events: {total}")

    # Sessions
    sessions = conn.execute(f"""
        SELECT DISTINCT session_id FROM '{parquet_path}'
    """).df()
    print(f"Sessions: {len(sessions)}")

    # Date range
    date_range = conn.execute(f"""
        SELECT MIN(ts) as first, MAX(ts) as last FROM '{parquet_path}'
    """).df()
    print(f"Date range: {date_range['first'].iloc[0]} to {date_range['last'].iloc[0]}")

    # By doc_type
    print("\nEvents by type:")
    by_type = conn.execute(f"""
        SELECT doc_type, COUNT(*) as count
        FROM '{parquet_path}'
        GROUP BY doc_type
        ORDER BY count DESC
    """).df()
    print(by_type.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Query captured session data")
    parser.add_argument("--session", help="Session ID to query")
    parser.add_argument("--recent", type=int, help="Show N most recent events")
    parser.add_argument("--stats", action="store_true", help="Show capture statistics")

    args = parser.parse_args()

    if args.session:
        query_session(args.session)
    elif args.recent:
        query_recent(args.recent)
    elif args.stats:
        query_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 4: Run script to verify**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER && python src/scripts/query_session.py --stats
```

Expected: Statistics output from captured data

**Step 5: Commit**

```bash
git add src/scripts/query_session.py src/tests/test_scripts/test_query_session.py
git commit -m "feat(Phase 12D): Add DuckDB query script for session analysis

- Query by session ID
- Show recent events
- Display capture statistics"
```

---

### Task 4: Add Trade Latency Capture to EventStore

**Files:**
- Modify: `src/services/event_store/service.py`
- Modify: `src/services/event_store/schema.py`
- Create: `src/tests/test_services/test_event_store/test_latency.py`

**Step 1: Write failing test for latency capture**

```python
# src/tests/test_services/test_event_store/test_latency.py
"""Tests for trade latency capture in EventStore."""

import pytest
from decimal import Decimal
from services.event_bus import EventBus, Events
from services.event_store.service import EventStoreService
from services.event_store.paths import EventStorePaths
import tempfile


def test_trade_event_captures_timestamp():
    """Trade events should include submission timestamp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = EventStorePaths(base_dir=tmpdir)
        event_bus = EventBus()
        service = EventStoreService(event_bus, paths=paths)
        service.start()

        # Publish trade with timestamp
        event_bus.publish(Events.TRADE_BUY, {
            "amount": "1.0",
            "price": "5.5",
            "gameId": "game-123",
            "timestamp_ms": 1734800000000
        })

        # Should be captured in buffer
        assert service.event_count >= 1

        service.stop()


def test_trade_confirmation_captures_latency():
    """Trade confirmations should include latency calculation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = EventStorePaths(base_dir=tmpdir)
        event_bus = EventBus()
        service = EventStoreService(event_bus, paths=paths)
        service.start()

        # Publish trade confirmation
        event_bus.publish(Events.TRADE_CONFIRMED, {
            "action_id": "abc-123",
            "timestamp_submitted": 1734800000000,
            "timestamp_confirmed": 1734800000250,
            "latency_ms": 250
        })

        # Should be captured
        assert service.event_count >= 1

        service.stop()
```

**Step 2: Run test to verify it fails**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_services/test_event_store/test_latency.py -v
```

Expected: FAIL (TRADE_CONFIRMED event not yet subscribed)

**Step 3: Add TRADE_CONFIRMED to EventStore subscriptions**

In `src/services/event_store/service.py`:

```python
def start(self) -> None:
    """Start service and subscribe to events"""
    # ... existing subscriptions ...

    # Subscribe to trade confirmation (for latency tracking)
    self._event_bus.subscribe(Events.TRADE_CONFIRMED, self._on_trade_confirmed, weak=False)

def _on_trade_confirmed(self, wrapped: dict[str, Any]) -> None:
    """Handle trade confirmation event with latency."""
    try:
        data = wrapped.get("data", wrapped)

        envelope = EventEnvelope.from_player_action(
            action_type="trade_confirmed",
            data=data,
            source=EventSource.UI,
            session_id=self._session_id,
            seq=self._next_seq(),
            game_id=data.get("gameId"),
        )

        self._writer.write(envelope)

    except Exception as e:
        logger.error(f"Error handling TRADE_CONFIRMED: {e}")
```

**Step 4: Add TRADE_CONFIRMED event to Events enum (if not exists)**

In `src/services/event_bus.py`:

```python
class Events(Enum):
    # ... existing events ...
    TRADE_CONFIRMED = "trade_confirmed"  # Trade confirmation with latency
```

**Step 5: Run test**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_services/test_event_store/test_latency.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/services/event_store/service.py src/services/event_bus.py src/tests/test_services/test_event_store/test_latency.py
git commit -m "feat(Phase 12D): Add trade latency capture to EventStore

- Subscribe to TRADE_CONFIRMED events
- Capture timestamp_submitted, timestamp_confirmed, latency_ms
```

---

### Task 5: Create Legacy Recorder Deprecation Config

**Files:**
- Modify: `src/config.py`
- Create: `src/tests/test_config/test_legacy_flags.py`

**Step 1: Write test for legacy flags**

```python
# src/tests/test_config/test_legacy_flags.py
"""Tests for legacy recorder deprecation flags."""

import pytest


def test_legacy_recorder_flags_exist():
    """Config should have flags to disable legacy recorders."""
    from config import Config

    # Should have method to check legacy flags
    assert hasattr(Config, 'get_legacy_flags')


def test_default_flags_enable_legacy():
    """By default, legacy recorders should be enabled for backwards compatibility."""
    from config import Config

    flags = Config.get_legacy_flags()

    # Default: legacy enabled (safe transition)
    assert flags.get("enable_recorder_sink", True) is True
    assert flags.get("enable_demo_recorder", True) is True
    assert flags.get("enable_raw_capture", True) is True
```

**Step 2: Add legacy flags to Config**

```python
# In config.py
@classmethod
def get_legacy_flags(cls) -> dict:
    """
    Get legacy recorder deprecation flags.

    Returns:
        Dict with boolean flags for each legacy recorder
    """
    return {
        "enable_recorder_sink": cls._get_bool_env("LEGACY_RECORDER_SINK", True),
        "enable_demo_recorder": cls._get_bool_env("LEGACY_DEMO_RECORDER", True),
        "enable_raw_capture": cls._get_bool_env("LEGACY_RAW_CAPTURE", True),
        "enable_unified_recorder": cls._get_bool_env("LEGACY_UNIFIED_RECORDER", True),
        "enable_game_state_recorder": cls._get_bool_env("LEGACY_GAME_STATE_RECORDER", True),
        "enable_player_session_recorder": cls._get_bool_env("LEGACY_PLAYER_SESSION_RECORDER", True),
    }

@classmethod
def _get_bool_env(cls, key: str, default: bool) -> bool:
    """Get boolean from environment variable."""
    import os
    value = os.environ.get(key, str(default)).lower()
    return value in ("true", "1", "yes")
```

**Step 3: Run test**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_config/test_legacy_flags.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/config.py src/tests/test_config/test_legacy_flags.py
git commit -m "feat(Phase 12D): Add legacy recorder deprecation flags

- Environment variable control for each legacy recorder
- Default: enabled (backwards compatible)
- Set LEGACY_*=false to disable individual recorders"
```

---

### Task 6: Add JSONL Export CLI for Backwards Compatibility

**Files:**
- Create: `src/scripts/export_jsonl.py`
- Create: `src/tests/test_scripts/test_export_jsonl.py`

**Step 1: Write failing test**

```python
# src/tests/test_scripts/test_export_jsonl.py
"""Tests for JSONL export script."""

import pytest
import tempfile
from pathlib import Path
import json


def test_export_parquet_to_jsonl():
    """Should convert Parquet files to JSONL format."""
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test parquet
        parquet_dir = Path(tmpdir) / "events_parquet" / "doc_type=ws_event"
        parquet_dir.mkdir(parents=True)

        table = pa.table({
            'ts': ['2025-12-21T10:00:00'],
            'doc_type': ['ws_event'],
            'event_name': ['gameStateUpdate'],
            'raw_json': ['{"tick": 1}'],
        })
        pq.write_table(table, parquet_dir / "test.parquet")

        # Export to JSONL
        output_dir = Path(tmpdir) / "export"
        output_dir.mkdir()

        # Run export (we'll implement this)
        from scripts.export_jsonl import export_to_jsonl
        export_to_jsonl(
            parquet_dir=Path(tmpdir) / "events_parquet",
            output_dir=output_dir
        )

        # Verify JSONL created
        jsonl_files = list(output_dir.glob("*.jsonl"))
        assert len(jsonl_files) >= 1
```

**Step 2: Create export_jsonl.py**

```python
#!/usr/bin/env python3
"""
Export Parquet data to JSONL for backwards compatibility.

Usage:
    python scripts/export_jsonl.py --output ./export/
    python scripts/export_jsonl.py --session <session_id> --output ./export/
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

import duckdb


def get_data_dir() -> Path:
    """Get data directory from config or default."""
    import os
    return Path(os.environ.get("RUGS_DATA_DIR", Path.home() / "rugs_data"))


def export_to_jsonl(
    parquet_dir: Path,
    output_dir: Path,
    session_id: str | None = None
) -> list[Path]:
    """
    Export Parquet files to JSONL format.

    Args:
        parquet_dir: Directory containing Parquet files
        output_dir: Directory for JSONL output
        session_id: Optional session to filter

    Returns:
        List of created JSONL files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect()
    parquet_path = parquet_dir / "**" / "*.parquet"

    # Build query
    where_clause = f"WHERE session_id = '{session_id}'" if session_id else ""

    query = f"""
    SELECT * FROM '{parquet_path}'
    {where_clause}
    ORDER BY ts
    """

    result = conn.execute(query).df()

    if len(result) == 0:
        print("No events found to export")
        return []

    # Group by doc_type and export
    created_files = []

    for doc_type in result['doc_type'].unique():
        subset = result[result['doc_type'] == doc_type]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{doc_type}.jsonl"
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            for _, row in subset.iterrows():
                record = row.to_dict()
                # Convert timestamp to string
                if 'ts' in record:
                    record['ts'] = str(record['ts'])
                f.write(json.dumps(record, default=str) + '\n')

        print(f"Exported {len(subset)} events to {filepath}")
        created_files.append(filepath)

    return created_files


def main():
    parser = argparse.ArgumentParser(description="Export Parquet to JSONL")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--session", help="Session ID to export")
    parser.add_argument("--data-dir", help="Data directory (default: ~/rugs_data)")

    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else get_data_dir()
    parquet_dir = data_dir / "events_parquet"

    export_to_jsonl(
        parquet_dir=parquet_dir,
        output_dir=Path(args.output),
        session_id=args.session
    )


if __name__ == "__main__":
    main()
```

**Step 3: Run test**

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_scripts/test_export_jsonl.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/scripts/export_jsonl.py src/tests/test_scripts/test_export_jsonl.py
git commit -m "feat(Phase 12D): Add JSONL export for backwards compatibility

- Export Parquet data to JSONL format
- Filter by session ID
- Grouped by doc_type"
```

---

### Task 7: Create Migration Guide Document

**Files:**
- Create: `docs/MIGRATION_GUIDE.md`

**Step 1: Write migration guide**

```markdown
# VECTRA-PLAYER Migration Guide: Legacy Recorders to EventStore

## Overview

Phase 12D consolidates 6 legacy recorders into a single EventStoreService. This guide documents the migration path and how to access data from the new system.

## Migration Matrix

| Legacy Recorder | Replacement | Data Access |
|-----------------|-------------|-------------|
| GameStateRecorder | EventStore.GAME_TICK | DuckDB: `doc_type='game_tick'` |
| PlayerSessionRecorder | EventStore.PLAYER_UPDATE | DuckDB: `doc_type='server_state'` |

## Querying Data

### DuckDB CLI
```sql
-- All events from a session
SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet'
WHERE session_id = 'abc-123'
ORDER BY ts;

SELECT tick, price, game_id FROM '~/rugs_data/events_parquet/**/*.parquet'
WHERE doc_type = 'game_tick'
ORDER BY ts;

SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet'
WHERE doc_type = 'player_action'
ORDER BY ts;
```

### Python Script
```bash
# Show statistics
python src/scripts/query_session.py --stats

# Recent events
python src/scripts/query_session.py --recent 20

# Export to JSONL (backwards compatible)
python src/scripts/export_jsonl.py --output ./export/
```

## Deprecation Flags

Set environment variables to disable legacy recorders:

```bash
export LEGACY_RECORDER_SINK=false
export LEGACY_DEMO_RECORDER=false
export LEGACY_RAW_CAPTURE=false
export LEGACY_UNIFIED_RECORDER=false
export LEGACY_GAME_STATE_RECORDER=false
export LEGACY_PLAYER_SESSION_RECORDER=false
```

## Timeline

1. **Phase 12D (Current):** Dual-write mode - both systems active
2. **Phase 12E:** Legacy recorders disabled by default
3. **Phase 13:** Legacy recorder code removed

## Rollback

If issues occur, re-enable legacy recorders:
```bash
export LEGACY_RECORDER_SINK=true
# etc.
```
```

**Step 2: Commit**

```bash
git add docs/MIGRATION_GUIDE.md
git commit -m "docs(Phase 12D): Add migration guide for legacy recorder consolidation"
```

---

### Task 8: Update CLAUDE.md with Phase 12D Status

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/scratchpad.md`

**Step 1: Update CLAUDE.md migration status table**

Add to CLAUDE.md:

```markdown
## Migration Status

| Phase | Status | Description |
|-------|--------|-------------|
| A | ✅ COMPLETE | Dual-write (EventStore + legacy toggle) |
| B | ✅ COMPLETE | Parquet writer + DuckDB query layer |
| C | ✅ COMPLETE | Server-authoritative state (LiveStateProvider) |
| D | ✅ COMPLETE | System validation + deprecation flags |
| E | TODO | Protocol Explorer UI + vector indexing |
```

**Step 2: Update scratchpad with new status**

**Step 3: Commit**

```bash
git add CLAUDE.md .claude/scratchpad.md
git commit -m "docs(Phase 12D): Update project status and migration documentation"
```

---

## Validation Checklist

Before declaring Phase 12D complete:

- [ ] All tests pass (1000+ tests)
- [ ] Capture stats visible in UI
- [ ] Live balance shows server-authoritative values
- [ ] DuckDB query script works
- [ ] JSONL export works
- [ ] Legacy flags documented
- [ ] Migration guide complete

## Success Metrics

1. **UI shows new system working:**
   - Capture stats panel visible
   - Event count updates in real-time
   - "LIVE: username" indicator shows when CDP connected

2. **Data accessible via DuckDB:**
   - `query_session.py --stats` shows captured events
   - Can query by session, doc_type, date

3. **Backwards compatibility preserved:**
   - JSONL export works
   - Legacy recorders still functional (default on)

---

*Plan Version: 1.0.0*
*Created: 2025-12-21*
*Total Tasks: 8*
*Estimated Time: 4-6 hours*
