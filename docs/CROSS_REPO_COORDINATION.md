# Cross-Repository Coordination

**Status:** Active
**Updated:** December 18, 2025

This document describes how VECTRA-PLAYER integrates with other repositories in the Rugs.fun ecosystem.

---

## Repository Overview

| Repository | Location | Role |
|------------|----------|------|
| **VECTRA-PLAYER** | `/home/nomad/Desktop/VECTRA-PLAYER/` | Data capture, replay, and UI |
| **claude-flow** | `/home/nomad/Desktop/claude-flow/` | Development orchestration, RAG agents |
| **rugs-rl-bot** | `/home/nomad/Desktop/rugs-rl-bot/` | ML training, RL bot |
| **Data Directory** | `~/rugs_data/` | Canonical storage (Parquet) |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VECTRA-PLAYER                                │
│                                                                     │
│  WebSocket ──► EventBus ──► EventStoreService ──► Parquet Files    │
│      │                                               │              │
│      │                                               ▼              │
│      ▼                                    ~/rugs_data/events_parquet/│
│  Live UI Display                                     │              │
│                                                      ▼              │
└───────────────────────────────────────────────────────┼─────────────┘
                                                        │
        ┌───────────────────────────────────────────────┼──────────────┐
        │                                               │              │
        ▼                                               ▼              │
┌───────────────────┐                        ┌─────────────────────────┐
│    claude-flow    │                        │      rugs-rl-bot       │
│                   │                        │                        │
│  rugs-expert      │◄── Query Parquet ──────│  SidebetPredictor      │
│  agent queries    │    via DuckDB          │  RL Environment        │
│  LanceDB vectors  │                        │  Training Scripts      │
└───────────────────┘                        └─────────────────────────┘
```

---

## Integration Points

### 1. VECTRA-PLAYER → Parquet (Canonical Truth)

**EventStoreService** persists all events to Parquet:

```
~/rugs_data/events_parquet/
├── doc_type=ws_event/
│   └── date=2025-12-18/
│       └── 20251218_143052_a1b2c3d4.parquet
├── doc_type=game_tick/
├── doc_type=player_action/
├── doc_type=server_state/
└── doc_type=system_event/
```

**Schema Version:** 1.0.0 (see `src/services/event_store/schema.py`)

### 2. claude-flow → VECTRA-PLAYER Data

The `rugs-expert` agent in claude-flow queries VECTRA-PLAYER's Parquet data:

**DuckDB Query Layer:**
```python
import duckdb
conn = duckdb.connect()
df = conn.execute("""
    SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet'
    WHERE doc_type = 'ws_event'
    AND event_name = 'gameStateUpdate'
    LIMIT 100
""").df()
```

**LanceDB Vector Search:** (Future - Phase 12E)
```python
import lancedb
db = lancedb.connect("~/rugs_data/vectors/events.lance")
results = db.table("events").search("What fields are in playerUpdate?").limit(10)
```

### 3. rugs-rl-bot → VECTRA-PLAYER Data

ML training reads from the same Parquet dataset:

**Sidebet Predictor Training:**
```python
# Load game data from Parquet
import duckdb
games_df = duckdb.execute("""
    SELECT game_id, tick, price, ts
    FROM '~/rugs_data/events_parquet/doc_type=game_tick/**/*.parquet'
    ORDER BY session_id, seq
""").df()
```

**RL Environment:**
- Reads game recordings for replay-based training
- Uses same data format as live WebSocket feed
- SidebetPredictor integrated into observation space

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUGS_DATA_DIR` | `~/rugs_data` | Base directory for all data |
| `RUGS_LEGACY_RECORDERS` | `true` | Set to `false` to disable legacy recorders |

### Migration Mode

To run in EventStore-only mode (no legacy recorders):

```bash
export RUGS_LEGACY_RECORDERS=false
./run.sh
```

This disables legacy recording and capture tooling.

All data still flows through EventStoreService to Parquet.

---

## Schema Compatibility

### Common Event Envelope

All doc_types share a common envelope:

| Field | Type | Description |
|-------|------|-------------|
| `ts` | datetime | Event timestamp (UTC) |
| `source` | string | cdp, public_ws, replay, ui |
| `doc_type` | string | Event type |
| `session_id` | string | Recording session UUID |
| `seq` | int | Sequence within session |
| `direction` | string | received, sent |
| `raw_json` | string | Full original payload |
| `game_id` | string? | Game identifier |
| `player_id` | string? | Player DID |
| `username` | string? | Player display name |

### Version Management

Schema version stored in `~/rugs_data/manifests/schema_version.json`:

```json
{
  "version": "1.0.0",
  "created": "2025-12-18T00:00:00Z",
  "fields": ["ts", "source", "doc_type", ...]
}
```

rugs-rl-bot and claude-flow should check schema version before processing.

---

## Coordination Checklist

### When Adding New Event Types

1. Update `src/services/event_store/schema.py` with new DocType
2. Add EventBus subscription in `EventStoreService`
3. Document in `docs/specs/WEBSOCKET_EVENTS_SPEC.md`
4. Notify rugs-rl-bot if affects ML features
5. Update claude-flow knowledge if needed

### When Changing Schema

1. Increment schema version
2. Add migration script if needed
3. Update all consumers (rugs-rl-bot, claude-flow)
4. Test backward compatibility

### When Deploying Changes

1. Run full test suite (`pytest tests/ -v`)
2. Verify Parquet writes work (`ls -la ~/rugs_data/events_parquet/`)
3. Test DuckDB queries still work
4. Update CLAUDE.md in affected repos

---

## Contact Points

- **VECTRA-PLAYER issues:** Data capture, UI, EventStore
- **claude-flow issues:** RAG queries, agent behavior
- **rugs-rl-bot issues:** ML training, RL environment

---

*Last updated: December 18, 2025*
