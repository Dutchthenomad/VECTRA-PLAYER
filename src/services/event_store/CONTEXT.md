# Event Store Module Context

**Module**: `src/services/event_store/`
**Last Updated**: 2025-12-17

## Overview

The Event Store module provides the unified data persistence layer for VECTRA-PLAYER. It implements a write-once, query-many architecture using Parquet files as the canonical data store with DuckDB as the query engine.

## Architecture

```
EventBus (producers)
       │
       ▼
EventStoreService (subscriber)
       │
       ▼
ParquetWriter (buffered atomic writes)
       │
       ▼
Parquet Files (partitioned by doc_type/date)
       │
       ▼
EventStoreQuery (DuckDB query interface)
```

## Components

### `schema.py` - Event Envelope & Types

Defines the canonical event schema:

- **DocType**: `ws_event`, `game_tick`, `player_action`, `server_state`, `system_event`
- **EventSource**: `cdp`, `public_ws`, `replay`, `ui`
- **Direction**: `received`, `sent`
- **EventEnvelope**: Dataclass with factory methods for each doc_type

### `paths.py` - Directory Management

Centralizes all path derivation from `RUGS_DATA_DIR` environment variable:

```
~/rugs_data/
├── events_parquet/
│   ├── doc_type=ws_event/
│   │   └── date=YYYY-MM-DD/
│   ├── doc_type=game_tick/
│   └── ...
├── vectors/
├── exports/
└── manifests/
```

### `writer.py` - Parquet Writer

Buffered, atomic writes with:
- Configurable buffer size (default: 100 events)
- Time-based auto-flush (default: 5 seconds)
- Atomic write pattern (temp file → rename)
- Thread-safe operations

### `service.py` - EventBus Integration

Subscribes to EventBus events and persists them:
- `Events.WS_RAW_EVENT` → `ws_event`
- `Events.GAME_TICK` → `game_tick`
- `Events.PLAYER_UPDATE` → `server_state`
- `Events.TRADE_*` → `player_action`

### `duckdb.py` - Query Layer

Stateless DuckDB query interface:

```python
from services.event_store import EventStoreQuery

query = EventStoreQuery()

# Game episode extraction (RL training)
episode = query.get_game_episode("game-123")
for game_df in query.iter_episodes(player_id="whale-xyz", limit=50):
    train_on(game_df)

# Feature engineering
features = query.get_tick_features("game-123")

# Discovery
games = query.list_games()
players = query.list_players()
count = query.count_events(doc_type="game_tick")
```

## Key Design Decisions

### Stateless Queries

Each query method creates a fresh DuckDB connection. This provides:
- Thread-safety by default
- No connection state to manage
- Negligible overhead (~1ms per connection)

### Parquet Partitioning

Files partitioned by `doc_type` and `date` for:
- Efficient queries filtering by doc_type
- Easy data lifecycle management (delete old dates)
- DuckDB partition pruning

### Feature Engineering in SQL

Window functions compute features directly in DuckDB:
- `price_change` - Tick-over-tick delta
- `volatility_5/10` - Rolling standard deviation
- `max_price` - Running maximum
- `drawdown` - Current vs max percentage

## Usage Patterns

### RL Training Pipeline

```python
query = EventStoreQuery()

# Iterate through games for training
for episode in query.iter_episodes(player_id="profitable-trader", min_ticks=50):
    features = query.get_tick_features(episode["game_id"].iloc[0])
    train_step(features)
```

### Analytics

```python
# Raw SQL access
df = query.query("""
    SELECT game_id, COUNT(*) as events
    FROM '{parquet_glob}'
    GROUP BY game_id
    ORDER BY events DESC
    LIMIT 10
""")
```

### UI Queries

```python
# Quick lookups
games = query.list_games(limit=20)
player_actions = query.get_player_actions("player-123")
```

## Testing

Tests in `tests/test_services/test_event_store/`:
- `test_writer.py` - ParquetWriter (32 tests)
- `test_service.py` - EventStoreService integration
- `test_duckdb.py` - EventStoreQuery (32 tests)

Run: `pytest tests/test_services/test_event_store/ -v`

## Related Issues

- Issue #9: Parquet writer with atomic commits
- Issue #10: DuckDB query layer
- Issue #25: Thread-safe sequence numbers
