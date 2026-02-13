# 04 - Data Persistence

## Purpose

Single-writer Parquet persistence for all game events:
1. Atomic writes with buffering
2. Schema versioning (v2.0.0)
3. DuckDB query interface
4. Deduplication by gameId

## Dependencies

```python
# Storage
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

# Internal
from services.event_store.writer import ParquetWriter
from services.event_store.service import EventStoreService
from services.event_store.schema import EventEnvelope, EventSource
from services.event_store.paths import EventStorePaths
```

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                       EventStoreService                                │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  EventBus ──────▶ Subscription Handler ──────▶ EventEnvelope         │
│                                                      │                │
│                                               ┌──────▼──────┐        │
│                                               │ ParquetWriter │        │
│                                               │ (Buffered)    │        │
│                                               └──────┬──────┘        │
│                                                      │                │
│  ┌───────────────────────────────────────────────────▼──────────────┐│
│  │                        ~/rugs_data/                              ││
│  │  ┌────────────────────────────────────────────────────────────┐ ││
│  │  │  events_parquet/                                            │ ││
│  │  │  ├── doc_type=ws_event/                                    │ ││
│  │  │  ├── doc_type=game_tick/                                   │ ││
│  │  │  ├── doc_type=player_action/                               │ ││
│  │  │  ├── doc_type=server_state/                                │ ││
│  │  │  ├── doc_type=complete_game/   (Training data)             │ ││
│  │  │  └── doc_type=button_event/    (RL training)               │ ││
│  │  └────────────────────────────────────────────────────────────┘ ││
│  └──────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. EventEnvelope Schema

```python
# src/services/event_store/schema.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
import uuid

class EventSource(Enum):
    """Event source identifier"""
    CDP = "cdp"
    PUBLIC_WS = "public_ws"
    UI = "ui"

@dataclass
class EventEnvelope:
    """Universal event wrapper for Parquet storage"""

    # Identity
    event_id: str
    session_id: str
    seq: int  # Sequence number within session

    # Classification
    doc_type: str  # ws_event, game_tick, player_action, etc.
    event_name: str  # Original event name

    # Timing
    client_ts: datetime
    server_ts: datetime | None = None

    # Context
    game_id: str | None = None
    player_id: str | None = None
    username: str | None = None

    # Source
    source: EventSource = EventSource.PUBLIC_WS

    # Payload
    data: dict = field(default_factory=dict)

    # Schema version
    schema_version: str = "2.0.0"

    @classmethod
    def from_ws_event(cls, event_name: str, data: dict, source: EventSource,
                      session_id: str, seq: int, game_id: str | None = None):
        """Create envelope from raw WebSocket event"""
        return cls(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            seq=seq,
            doc_type="ws_event",
            event_name=event_name,
            client_ts=datetime.now(timezone.utc),
            game_id=game_id,
            source=source,
            data=data
        )

    @classmethod
    def from_game_tick(cls, tick: int, price: Decimal, data: dict, **kwargs):
        """Create envelope from game tick"""
        return cls(
            doc_type="game_tick",
            event_name="game_tick",
            data={"tick": tick, "price": float(price), **data},
            **kwargs
        )

    @classmethod
    def from_complete_game(cls, game_data: dict, **kwargs):
        """Create envelope from complete game (training data)"""
        return cls(
            doc_type="complete_game",
            event_name="complete_game",
            game_id=game_data.get("id") or game_data.get("gameId"),
            data=game_data,
            **kwargs
        )
```

### 2. ParquetWriter with Buffering

```python
# src/services/event_store/writer.py

class ParquetWriter:
    """Buffered Parquet writer with atomic flushes"""

    def __init__(self, paths: EventStorePaths, buffer_size: int = 100,
                 flush_interval: float = 5.0):
        self._paths = paths
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._buffer: list[EventEnvelope] = []
        self._lock = threading.Lock()
        self._last_flush = time.time()

        # Start flush timer
        self._timer_thread = threading.Thread(
            target=self._flush_timer,
            daemon=True
        )
        self._timer_thread.start()

    def write(self, envelope: EventEnvelope):
        """Add event to buffer, flush if needed"""
        with self._lock:
            self._buffer.append(envelope)

            if len(self._buffer) >= self._buffer_size:
                self._do_flush()

    def flush(self) -> list | None:
        """Force flush of buffer"""
        with self._lock:
            return self._do_flush()

    def _do_flush(self) -> list | None:
        """Actually write buffer to Parquet (must hold lock)"""
        if not self._buffer:
            return None

        # Group by doc_type for partitioned writes
        by_doc_type: dict[str, list] = {}
        for env in self._buffer:
            if env.doc_type not in by_doc_type:
                by_doc_type[env.doc_type] = []
            by_doc_type[env.doc_type].append(env)

        written_files = []

        for doc_type, envelopes in by_doc_type.items():
            # Convert to Arrow table
            table = self._to_arrow_table(envelopes)

            # Write to partitioned path
            partition_path = self._paths.events_dir / f"doc_type={doc_type}"
            partition_path.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"events_{timestamp}.parquet"
            filepath = partition_path / filename

            # Atomic write (write to temp, then rename)
            temp_path = filepath.with_suffix(".tmp")
            pq.write_table(table, temp_path)
            temp_path.rename(filepath)

            written_files.append(str(filepath))

        # Clear buffer
        self._buffer = []
        self._last_flush = time.time()

        return written_files

    def _to_arrow_table(self, envelopes: list[EventEnvelope]) -> pa.Table:
        """Convert envelopes to Arrow table"""
        import json

        records = []
        for env in envelopes:
            records.append({
                "event_id": env.event_id,
                "session_id": env.session_id,
                "seq": env.seq,
                "doc_type": env.doc_type,
                "event_name": env.event_name,
                "client_ts": env.client_ts.isoformat(),
                "server_ts": env.server_ts.isoformat() if env.server_ts else None,
                "game_id": env.game_id,
                "player_id": env.player_id,
                "username": env.username,
                "source": env.source.value,
                "data": json.dumps(env.data),
                "schema_version": env.schema_version,
            })

        return pa.Table.from_pylist(records)
```

### 3. EventStoreService (Single Writer)

```python
# src/services/event_store/service.py

class EventStoreService:
    """Single writer for all event persistence"""

    def __init__(self, event_bus: EventBus, paths: EventStorePaths | None = None,
                 session_id: str | None = None):
        self._event_bus = event_bus
        self._paths = paths or EventStorePaths()
        self._session_id = session_id or str(uuid.uuid4())
        self._seq = 0
        self._seq_lock = threading.Lock()

        self._writer = ParquetWriter(paths=self._paths)

        # Recording state
        self._started = False
        self._paused = True  # Start paused by default
        self._recorded_game_ids: set[str] = set()  # Deduplication

    def start(self):
        """Subscribe to events and start recording"""
        self._event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event, weak=False)
        self._event_bus.subscribe(Events.GAME_TICK, self._on_game_tick, weak=False)
        self._event_bus.subscribe(Events.BUTTON_PRESS, self._on_button_press, weak=False)
        # ... more subscriptions

        self._started = True

    def _on_ws_raw_event(self, wrapped: dict):
        """Handle raw WebSocket events"""
        if self._paused:
            return

        data = self._unwrap_event_payload(wrapped)
        if not data:
            return

        event_name = data.get("event")
        event_data = data.get("data") or {}

        # Create envelope
        envelope = EventEnvelope.from_ws_event(
            event_name=event_name,
            data=event_data,
            source=EventSource.CDP,
            session_id=self._session_id,
            seq=self._next_seq(),
            game_id=event_data.get("gameId")
        )

        self._writer.write(envelope)

        # Extract training data from gameHistory
        if event_name == "gameStateUpdate":
            game_history = event_data.get("gameHistory", [])
            self._capture_complete_games(game_history)

    def _capture_complete_games(self, game_history: list):
        """Capture complete games for training (with deduplication)"""
        for game in game_history:
            game_id = game.get("id") or game.get("gameId")
            if game_id and game_id not in self._recorded_game_ids:
                self._recorded_game_ids.add(game_id)

                envelope = EventEnvelope.from_complete_game(
                    game_data=game,
                    source=EventSource.CDP,
                    session_id=self._session_id,
                    seq=self._next_seq()
                )
                self._writer.write(envelope)
```

### 4. DuckDB Query Interface

```python
# Query Parquet files with DuckDB
import duckdb

def query_games(data_dir: str = "~/rugs_data") -> pd.DataFrame:
    """Query all complete games"""
    conn = duckdb.connect()
    return conn.execute(f"""
        SELECT
            json_extract_string(data, '$.id') as game_id,
            json_extract(data, '$.prices') as prices,
            json_extract(data, '$.peak') as peak,
            json_extract(data, '$.duration') as duration
        FROM '{data_dir}/events_parquet/doc_type=complete_game/*.parquet'
        ORDER BY client_ts DESC
    """).df()

def query_recent_ticks(game_id: str, limit: int = 100) -> pd.DataFrame:
    """Query recent ticks for a game"""
    conn = duckdb.connect()
    return conn.execute(f"""
        SELECT
            json_extract(data, '$.tick') as tick,
            json_extract(data, '$.price') as price,
            client_ts
        FROM '~/rugs_data/events_parquet/doc_type=game_tick/*.parquet'
        WHERE game_id = '{game_id}'
        ORDER BY seq DESC
        LIMIT {limit}
    """).df()
```

## Directory Structure

```
~/rugs_data/
├── events_parquet/
│   ├── doc_type=ws_event/
│   │   ├── events_20260118_143052_123456.parquet
│   │   └── ...
│   ├── doc_type=game_tick/
│   ├── doc_type=player_action/
│   ├── doc_type=server_state/
│   ├── doc_type=complete_game/
│   ├── doc_type=button_event/
│   └── doc_type=system_event/
├── manifests/
│   └── schema_version.json
├── .recording_control.json   # IPC: Flask → EventStore
└── .recording_status.json    # IPC: EventStore → Flask
```

## IPC Files (Flask ↔ EventStore)

### Control File (Flask → EventStore)

```python
# Flask writes to control recording
control = {
    "recording": True,  # or False
    "timestamp": time.time()
}
with open("~/.rugs_data/.recording_control.json", "w") as f:
    json.dump(control, f)
```

### Status File (EventStore → Flask)

```python
# EventStore writes status
status = {
    "is_recording": True,
    "event_count": 1234,
    "game_count": 56,
    "session_id": "abc123...",
    "updated_at": "2026-01-18T14:30:52Z"
}
# Atomic write
with open(temp_file, "w") as f:
    json.dump(status, f)
temp_file.rename(status_file)
```

## Integration Points

### With EventBus

```python
# EventStoreService subscribes to all relevant events
def start(self):
    self._event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event, weak=False)
```

### With Flask Dashboard

```python
# Dashboard reads status via IPC file
def get_status():
    with open("~/.rugs_data/.recording_status.json") as f:
        return json.load(f)

# Dashboard toggles recording via EventStoreService directly
event_store_service.toggle_recording()
```

## Configuration

### Paths

```python
# src/services/event_store/paths.py

class EventStorePaths:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.home() / "rugs_data"
        self.events_dir = self.base_dir / "events_parquet"
        self.manifests_dir = self.base_dir / "manifests"
```

### Buffer Settings

```python
buffer_size = 100       # Events before flush
flush_interval = 5.0    # Seconds between time-based flushes
```

## Gotchas

1. **gameHistory Deduplication**: Same game appears ~10 times in rolling window. Track `recorded_game_ids` set.

2. **Atomic Writes**: Write to `.tmp` then rename. Prevents corrupt files on crash.

3. **JSON in Parquet**: `data` field stores JSON string. Use `json_extract()` in DuckDB queries.

4. **Single Writer**: Only EventStoreService writes. Other services publish to EventBus.

5. **IPC Staleness**: Control file commands older than 10 seconds are ignored to prevent stale commands.

6. **Schema Version**: Track in manifest for forward compatibility. Current: v2.0.0.

7. **Partitioning**: Partition by `doc_type` for efficient queries. Each doc_type has separate directory.
