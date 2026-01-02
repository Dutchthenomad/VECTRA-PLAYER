# VECTRA-PLAYER Migration Guide: Legacy Recorders to EventStore

## Overview

Phase 12D consolidated 6 legacy recorders into a single EventStoreService. **This migration is COMPLETE as of December 2025.**

## Migration Status: COMPLETE

All legacy recorders have been removed. The EventStore is now the sole data persistence layer.

| Legacy Recorder | Status | Replacement |
|-----------------|--------|-------------|
| RecorderSink | **REMOVED** | EventStore.GAME_TICK |
| DemoRecorder | **REMOVED** | EventStore.PLAYER_ACTION |
| RawCaptureRecorder | **REMOVED** | EventStore.WS_EVENT |
| UnifiedRecorder | **REMOVED** | EventStore |
| GameStateRecorder | **REMOVED** | EventStore.GAME_TICK |
| PlayerSessionRecorder | **REMOVED** | EventStore.SERVER_STATE |

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

## Timeline (Historical)

1. **Phase 12A-12C:** EventStore implementation and validation
2. **Phase 12D:** Dual-write mode, legacy deprecation flags added
3. **Phase 13 (COMPLETE):** Legacy recorder code removed

## Data Directory

All data now lives in the canonical location:

```
~/rugs_data/
├── events_parquet/          # Canonical truth store
│   ├── doc_type=ws_event/
│   ├── doc_type=game_tick/
│   ├── doc_type=player_action/
│   └── doc_type=server_state/
├── exports/                 # Optional JSONL exports
└── manifests/
    └── schema_version.json
```
