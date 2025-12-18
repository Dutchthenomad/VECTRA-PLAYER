# DuckDB Query Layer Design

**Issue**: #10 - [Infra] DuckDB query layer
**Date**: 2025-12-17
**Status**: Approved

---

## Overview

Implement a DuckDB query interface for reading Parquet event data. Primary use case is RL training pipeline, with secondary support for analytics and UI queries.

## Requirements

From Issue #10:
- Query Parquet files directly (no ETL)
- SQL window functions for feature engineering
- Game episode extraction
- Player state reconstruction

## Design Decisions

### Approach: Stateless Query Functions

Each query method creates a fresh DuckDB connection, executes, returns results, and closes. This provides:
- Thread-safety by default
- No connection state to manage
- Negligible overhead (~1ms per connection)

Alternative considered: Connection context manager for session-scoped views. Deferred - can add later if needed.

### Priority Order

1. **RL Training** - Batch game episode extraction, player filtering
2. **Analytics** - Ad-hoc SQL queries, aggregations
3. **UI** - Low-latency recent event queries

## API Design

### Module: `src/services/event_store/duckdb.py`

### Class: `EventStoreQuery`

```python
class EventStoreQuery:
    """Stateless DuckDB query interface for Parquet event data."""

    def __init__(self, paths: EventStorePaths | None = None):
        """Initialize with paths config. Uses defaults if None."""

    # === Core Query Methods ===

    def query(self, sql: str, params: dict = None) -> pd.DataFrame:
        """Execute SQL and return pandas DataFrame."""

    def query_arrow(self, sql: str, params: dict = None) -> pa.Table:
        """Execute SQL and return PyArrow Table (zero-copy)."""

    # === Game Episode Extraction (RL Training) ===

    def get_game_episode(self, game_id: str) -> pd.DataFrame:
        """
        Get all events for a single game, sorted by sequence.

        Returns DataFrame with columns from all doc_types:
        ts, source, doc_type, session_id, seq, direction, raw_json,
        game_id, player_id, username, event_name, price, tick,
        action_type, cash, position_qty
        """

    def iter_episodes(
        self,
        player_id: str | None = None,
        min_ticks: int | None = None,
        limit: int | None = None,
    ) -> Iterator[pd.DataFrame]:
        """
        Iterate over game episodes as DataFrames.

        Args:
            player_id: Filter to games with this player
            min_ticks: Filter to games with at least N ticks
            limit: Maximum number of games to return

        Yields:
            DataFrame per game, sorted by seq
        """

    def get_episodes_batch(
        self,
        game_ids: list[str],
    ) -> dict[str, pd.DataFrame]:
        """Get multiple episodes in one query (more efficient)."""

    # === Player Queries ===

    def get_player_games(
        self,
        player_id: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get all events for a player's games."""

    def get_player_actions(
        self,
        player_id: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get player_action events only."""

    # === Discovery / Listing ===

    def list_games(self, limit: int = 100) -> list[str]:
        """List unique game_ids in the dataset."""

    def list_players(self, limit: int = 100) -> list[str]:
        """List unique player_ids in the dataset."""

    def count_events(self, doc_type: str | None = None) -> int:
        """Count total events, optionally filtered by doc_type."""

    # === Feature Engineering Views ===

    def get_tick_features(self, game_id: str) -> pd.DataFrame:
        """
        Get game ticks with computed features.

        Columns:
        - tick, price, ts
        - price_change (vs previous tick)
        - price_pct_change
        - volatility_5 (rolling 5-tick std dev)
        - volatility_10 (rolling 10-tick std dev)
        - max_price (running max)
        - drawdown (current price vs max)
        """
```

## SQL Patterns

### Game Episode Query
```sql
SELECT *
FROM '{parquet_glob}'
WHERE game_id = $game_id
ORDER BY seq
```

### Tick Features with Window Functions
```sql
SELECT
    tick,
    price,
    ts,
    price - LAG(price) OVER w AS price_change,
    (price - LAG(price) OVER w) / LAG(price) OVER w AS price_pct_change,
    STDDEV(price) OVER (ORDER BY seq ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS volatility_5,
    STDDEV(price) OVER (ORDER BY seq ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS volatility_10,
    MAX(price) OVER (ORDER BY seq ROWS UNBOUNDED PRECEDING) AS max_price,
    price / MAX(price) OVER (ORDER BY seq ROWS UNBOUNDED PRECEDING) - 1 AS drawdown
FROM '{parquet_glob}'
WHERE game_id = $game_id AND doc_type = 'game_tick'
WINDOW w AS (ORDER BY seq)
ORDER BY seq
```

### List Games with Player
```sql
SELECT DISTINCT game_id
FROM '{parquet_glob}'
WHERE player_id = $player_id
LIMIT $limit
```

## Internal Implementation

### Connection Helper
```python
def _connect(self) -> duckdb.DuckDBPyConnection:
    """Create fresh connection with Parquet glob configured."""
    conn = duckdb.connect()
    # DuckDB auto-discovers schema from Parquet
    return conn

def _parquet_glob(self, doc_type: str | None = None) -> str:
    """Build glob pattern for Parquet files."""
    if doc_type:
        return str(self._paths.events_parquet_dir / f"doc_type={doc_type}/**/*.parquet")
    return str(self._paths.events_parquet_dir / "**/*.parquet")
```

## Testing Strategy

1. **Fixtures**: Create temp Parquet files with known data using ParquetWriter
2. **Unit tests**: Each query method with edge cases
3. **Integration tests**: Full workflow (write events, query back)

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/services/event_store/duckdb.py` | Create |
| `src/services/event_store/__init__.py` | Add export |
| `src/tests/test_services/test_event_store/test_duckdb.py` | Create |
| `src/services/event_store/CONTEXT.md` | Create |

## Acceptance Criteria

- [x] Design approved
- [ ] DuckDB connection management
- [ ] Query helpers for common patterns
- [ ] Feature extraction SQL views
- [ ] Tests with sample Parquet data
- [ ] CONTEXT.md for duckdb.py
