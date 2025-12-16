# VECTRA-PLAYER - Unified Data Architecture for Rugs.fun

**Status:** Phase 12 Development | **Date:** December 15, 2025 | **Fork of:** REPLAYER

---

## Mission

VECTRA-PLAYER is a clean-slate refactor of REPLAYER focused on:
1. **Unified data storage** - DuckDB/Parquet as canonical truth + LanceDB for vectors
2. **Server-authoritative state** - Trust server in live mode, eliminate local calculations
3. **RAG integration** - LanceDB powers `rugs-expert` agent and Protocol Explorer UI
4. **Technical debt cleanup** - Remove deprecated code, eliminate hardcoded paths

**Core Principle:** Parquet is canonical truth; vector indexes are derived and rebuildable.

---

## Development Workflow: Superpowers Methodology

### Quick Reference
```bash
/tdd      # TDD Iron Law - NO code without failing test first
/verify   # Verification - Evidence before claims
/debug    # 4-phase root cause analysis
/plan     # Zero-context executable plans
/worktree # Isolated workspace per feature
```

### Test Command
```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short
```

---

## Architecture Overview

### Data Directory Structure
```
~/rugs_data/                          # RUGS_DATA_DIR (env var)
├── CONTEXT.md                        # Future AI reference doc
├── events_parquet/                   # Canonical truth store
│   ├── doc_type=ws_event/
│   ├── doc_type=game_tick/
│   ├── doc_type=player_action/
│   ├── doc_type=server_state/
│   └── doc_type=system_event/
├── vectors/                          # Derived LanceDB index
│   └── events.lance/
├── exports/                          # Optional JSONL exports
└── manifests/
    ├── schema_version.json
    └── vector_index_checkpoint.json
```

### Event Schema (v1.0.0)

**Common Envelope (all doc_types):**
| Field | Type | Description |
|-------|------|-------------|
| `ts` | datetime | Event timestamp (UTC) |
| `source` | string | 'cdp' \| 'public_ws' \| 'replay' \| 'ui' |
| `doc_type` | string | ws_event, game_tick, player_action, server_state, system_event |
| `session_id` | string | Recording session UUID |
| `game_id` | string? | Game identifier |
| `player_id` | string? | Player DID |
| `username` | string? | Player display name |
| `seq` | int | Sequence number within session |
| `direction` | string | 'received' \| 'sent' |
| `raw_json` | string | Full original payload |

---

## Key Components

### Single Writer: EventStore
```
src/services/event_store/
├── writer.py       # Buffering, atomic parquet writes
├── schema.py       # Pydantic/dataclasses + version
├── duckdb.py       # Query helpers
└── paths.py        # Derive all dirs from config/env
```

**All producers publish to EventBus; EventStore subscribes and persists:**
- `Events.WS_RAW_EVENT` → `ws_event`
- `Events.GAME_TICK` → `game_tick`
- `Events.PLAYER_UPDATE` → `server_state`
- Trading/UI actions → `player_action`
- Connection changes → `system_event`

### Vector Indexer: LanceDB
```
src/services/vector_indexer/
├── indexer.py      # Parquet → chunk → embed → upsert
├── chunker.py      # Doc-type specific chunking
└── embeddings.py   # Sentence-transformers wrapper
```

**Rebuild commands:**
```bash
vectra-player index build --full        # Full rebuild from Parquet
vectra-player index build --incremental # New data only
```

---

## Migration Status

| Phase | Status | Description |
|-------|--------|-------------|
| A | TODO | Dual-write (EventStore + legacy) |
| B | TODO | Backfill historical data + vector index |
| C | TODO | Server-authoritative state in UI |
| D | TODO | Remove legacy recorders |
| E | TODO | Protocol Explorer UI |

### "No Legacy Lingering" Checklist
- [ ] No module writes directly to filesystem except EventStore
- [ ] No hardcoded `/home/nomad/...` paths in runtime code
- [ ] No duplicate capture directories (raw_captures, rag_events, etc.)
- [ ] Tests enforce EventStore is sole writer

---

## Related Systems

| System | Location | Integration |
|--------|----------|-------------|
| claude-flow | `/home/nomad/Desktop/claude-flow/` | Dev layer (separate) |
| rugs-rl-bot | `/home/nomad/Desktop/rugs-rl-bot/` | RL training, ML models |
| REPLAYER | `/home/nomad/Desktop/REPLAYER/` | Production system |
| Data Directory | `~/rugs_data/` | Canonical storage |

### claude-flow Integration
- claude-flow stays **separate** as development/orchestration layer
- VECTRA-PLAYER builds new RAG with DuckDB/LanceDB
- claude-flow's `rugs-expert` agent will query VECTRA's LanceDB
- Reference knowledge: `/home/nomad/Desktop/claude-flow/knowledge/rugs-events/`

---

## Design Documents

| Document | Location |
|----------|----------|
| Storage Migration Plan | `sandbox/duckdb_parquet_lancedb_migration_plan.md` |
| Phase 12 Design | `sandbox/2025-12-15-phase-12-unified-data-architecture-design.md` |
| WebSocket Events Spec | `docs/specs/WEBSOCKET_EVENTS_SPEC.md` |
| Data Context | `~/rugs_data/CONTEXT.md` |

---

## Commands

### Run & Test
```bash
./run.sh                                     # Launch app
cd src && python3 -m pytest tests/ -v        # All tests
```

### DuckDB Queries
```python
import duckdb
conn = duckdb.connect()
df = conn.execute("SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet' LIMIT 10").df()
```

### Vector Indexing
```bash
# Build index from Parquet
vectra-player index build --full

# Query the index
vectra-player index query "What fields are in playerUpdate?"
```

---

## GitHub Repository

**Repo:** `Dutchthenomad/VECTRA-PLAYER`
**URL:** https://github.com/Dutchthenomad/VECTRA-PLAYER

---

*December 15, 2025 | Phase 12 Development*
