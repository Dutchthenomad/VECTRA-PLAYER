# Cross-Repository Coordination

**Status:** Active
**Updated:** December 19, 2025

This document describes how VECTRA-PLAYER integrates with other repositories in the Rugs.fun ecosystem.

---

## Repository Overview

| Repository | Role | Authority |
|------------|------|-----------|
| **VECTRA-PLAYER** | Data capture, replay, and UI | Event schemas, Parquet storage |
| **claude-flow** | Development orchestration, RAG agents | **Canonical rugs.fun backend authority** |
| **rugs-rl-bot** | ML training, RL bot | ML models, training pipelines |
| **Data Directory** (`~/rugs_data/`) | Canonical storage (Parquet) | Single source of truth for captured data |

> **Note:** `claude-flow/rugs-expert` agent is the canonical authority on rugs.fun backend behavior.
> Open research questions should be documented in `docs/issues/RUGS_BACKEND_RESEARCH_QUESTIONS.md`
> and filed as GitHub issues in claude-flow.

---

## Data Source Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RUGS.FUN DATA SOURCE HIERARCHY                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TIER 1: Public WebSocket (Unauthenticated)                    [AVAILABLE] │
│  ├── gameStateUpdate.gameHistory[]  → Historical games (~10)               │
│  │   └── Full tick-by-tick price arrays for ML training                    │
│  │   └── Used for Provably Fair verification system                        │
│  ├── gameStateUpdate.leaderboard[]  → All player positions/PnL             │
│  ├── gameStateUpdate (live ticks)   → Current game state (303+ fields)     │
│  └── partialPrices                  → Backfill for missed ticks            │
│                                                                             │
│  TIER 2: CDP/Authenticated (When Profile Connected)            [REQUIRES AUTH]│
│  ├── playerUpdate                   → Server-authoritative balance         │
│  │   └── cash, positionQty, avgCost, cumulativePnL, totalInvested         │
│  │   └── Fires ~250ms intervals when profile connected                     │
│  ├── gameStatePlayerUpdate          → Rugpool lottery details              │
│  └── Trade responses                → Latency/execution metrics            │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  RESEARCH STATUS: See docs/issues/RUGS_BACKEND_RESEARCH_QUESTIONS.md       │
│  - gameHistory count/timing: NEEDS VERIFICATION                            │
│  - Field completeness: NEEDS RAW DATA ANALYSIS                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Provenance Warning

Current RAG agent analysis is based on **normalized/parsed data**, not raw server frames:

```
Raw rugs.fun WebSocket → Parser Layer → Normalized JSONL → Analysis
                              ↑
                     PARSING ARTIFACTS POSSIBLE
```

**Reliable:** Direct field copies (`prices[]`, `rugged`, `peakMultiplier`)
**Uncertain:** Phase classifications, trade counts, temporal metrics

Raw captures exist at `~/rugs_recordings/raw_captures/` but require proper chunking
and vector DB ingestion before LLM analysis (too large for brute force).

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

This disables:
- `DemoRecorderSink` (JSONL demonstrations)
- `RawCaptureRecorder` (debug JSONL captures)
- `UnifiedRecorder` (game state + player action JSON)

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

## Open Research

See `docs/issues/RUGS_BACKEND_RESEARCH_QUESTIONS.md` for:
- gameHistory count and broadcast timing verification
- playerUpdate trigger conditions
- Field completeness analysis
- Raw data ingestion plan

---

*Last updated: December 19, 2025*
