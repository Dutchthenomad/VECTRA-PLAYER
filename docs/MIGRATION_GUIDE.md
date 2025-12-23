# VECTRA-PLAYER Migration Guide: Legacy Recorders to EventStore

## Overview

Phase 12D consolidates 6 legacy recorders into a single EventStoreService. This guide documents the migration path.

## Migration Matrix

| Legacy Recorder | Replacement | Data Access |
|-----------------|-------------|-------------|
| GameStateRecorder | EventStore.GAME_TICK | `doc_type='game_tick'` |
| PlayerSessionRecorder | EventStore.PLAYER_UPDATE | `doc_type='server_state'` |

## Querying Data

### DuckDB CLI
```sql
-- All events from a session
SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet'
WHERE session_id = 'abc-123'
ORDER BY ts;

SELECT tick, price, game_id FROM '~/rugs_data/events_parquet/**/*.parquet'
WHERE doc_type = 'game_tick';

SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet'
WHERE doc_type = 'player_action' AND action_type = 'trade_confirmed';
```

### Python Scripts
```bash
# Show statistics
python src/scripts/query_session.py --stats

# Recent events
python src/scripts/query_session.py --recent 20

# Export to JSONL (backwards compatible)
python src/scripts/export_jsonl.py --output ./export/
```

## Deprecation Flags

Control legacy recorders via environment variables:

```bash
export LEGACY_RECORDER_SINK=false
export LEGACY_DEMO_RECORDER=false
export LEGACY_RAW_CAPTURE=false
export LEGACY_UNIFIED_RECORDER=false
export LEGACY_GAME_STATE_RECORDER=false
export LEGACY_PLAYER_SESSION_RECORDER=false
```

Default: All `true` (backwards compatible)

## Timeline

1. **Phase 12D (Current):** Dual-write mode - both systems active
2. **Phase 12E:** Legacy recorders disabled by default
3. **Phase 13:** Legacy recorder code removed

## Rollback

Re-enable legacy recorders if needed:
```bash
export LEGACY_RECORDER_SINK=true
```
