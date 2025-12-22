# VECTRA-PLAYER - Unified Data Architecture for Rugs.fun

**Status:** Phase 12D Active | **Date:** December 21, 2025 | **Fork of:** REPLAYER

---

## Mission

VECTRA-PLAYER is a clean-slate refactor of REPLAYER focused on:
1. **Unified data storage** - DuckDB/Parquet as canonical truth + ChromaDB for vectors
2. **Server-authoritative state** - Trust server in live mode, eliminate local calculations
3. **RAG integration** - ChromaDB powers `rugs-expert` agent and Protocol Explorer UI
4. **Technical debt cleanup** - Remove deprecated code, eliminate hardcoded paths

**Core Principle:** Parquet is canonical truth; vector indexes are derived and rebuildable.

**December 20, 2025:** Changed vector store from LanceDB to **ChromaDB** to reuse existing claude-flow infrastructure (~600 LOC). ChromaDB MCP server available for Claude Code integration.

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
├── exports/                          # Optional JSONL exports
└── manifests/
    ├── schema_version.json
    └── vector_index_checkpoint.json

# ChromaDB lives in claude-flow (reused infrastructure)
~/Desktop/claude-flow/rag-pipeline/storage/chroma/
├── chroma.sqlite3                    # Vector database
└── [collection dirs]                 # Embedding storage
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

### Vector Indexer: ChromaDB (Reuses claude-flow)

**Reusable Components from claude-flow:**
```
claude-flow/rag-pipeline/
├── storage/store.py       # ChromaDB client wrapper (~150 LOC)
├── embeddings/embedder.py # Sentence-transformers (~100 LOC)
├── ingestion/chunker.py   # Markdown-aware chunking (~200 LOC)
├── ingestion/event_chunker.py # WebSocket event chunking (~100 LOC)
└── retrieval/retrieve.py  # Query interface (~100 LOC)
```

**ChromaDB MCP Server Tools:**
```python
mcp__chroma__chroma_list_collections
mcp__chroma__chroma_add_documents
mcp__chroma__chroma_query_documents
```

**Collections:**
- `claude_flow_knowledge` - Agent/skills documentation
- `rugs_events` - WebSocket event data (NEW)

---

## Migration Status

| Phase | Status | Description |
|-------|--------|-------------|
| 12A | ✅ COMPLETE | Event schemas (58 tests) |
| 12B | ✅ COMPLETE | Parquet Writer + EventStore (84 tests) |
| 12C | ✅ COMPLETE | LiveStateProvider (20 tests) |
| 12D | ✅ IN PROGRESS | System validation & legacy consolidation |
| 12E | ⏳ PENDING | Protocol Explorer UI |

### Phase 12D Completed (Dec 21, 2025)
- ✅ Capture Stats Panel in UI (event count, file count, session ID)
- ✅ Live Balance Display with visual indicator
- ✅ DuckDB query script (`src/scripts/query_session.py`)
- ✅ Trade latency capture (TRADE_CONFIRMED event)
- ✅ Legacy deprecation flags (6 env vars)
- ✅ JSONL export CLI (`src/scripts/export_jsonl.py`)
- ✅ Migration Guide (`docs/MIGRATION_GUIDE.md`)

### Legacy Deprecation Flags
```bash
export LEGACY_RECORDER_SINK=false       # RecorderSink
export LEGACY_DEMO_RECORDER=false       # DemoRecorderSink
export LEGACY_RAW_CAPTURE=false         # RawCaptureRecorder
export LEGACY_UNIFIED_RECORDER=false    # UnifiedRecorder
export LEGACY_GAME_STATE_RECORDER=false # GameStateRecorder
export LEGACY_PLAYER_SESSION_RECORDER=false # PlayerSessionRecorder
```
Default: All `true` (backwards compatible)

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
- VECTRA-PLAYER reuses claude-flow's ChromaDB RAG infrastructure
- claude-flow's `rugs-expert` agent queries shared ChromaDB
- Reference knowledge: `/home/nomad/Desktop/claude-flow/knowledge/rugs-events/`
- ChromaDB location: `/home/nomad/Desktop/claude-flow/rag-pipeline/storage/chroma/`

---

## Design Documents

| Document | Location |
|----------|----------|
| Migration Guide | `docs/MIGRATION_GUIDE.md` |
| Phase 12D Plan | `docs/plans/2025-12-21-phase-12d-system-validation-and-legacy-consolidation.md` |
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

*December 21, 2025 | Phase 12D - System Validation & Legacy Consolidation*
