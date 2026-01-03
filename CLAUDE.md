# VECTRA-PLAYER - Unified Data Architecture for Rugs.fun

**Status:** Schema v2.0.0 | **Date:** January 2, 2026 | **Fork of:** REPLAYER

---

## ⚠️ CRITICAL: Chrome Profile Configuration

**ALWAYS USE THE `rugs_bot` PROFILE - NO EXCEPTIONS!**

```
Profile Path: ~/.gamebot/chrome_profiles/rugs_bot/
Config Key: CHROME_PROFILE=rugs_bot (default in config.py)
```

This profile has:
- ✅ Phantom wallet extension installed and configured
- ✅ Wallet connected to rugs.fun
- ✅ CDP (Chrome DevTools Protocol) works correctly

**DO NOT use the Default profile** (`~/.config/google-chrome/`) - it has CDP binding issues.

See: `docs/CHROME_PROFILE_SETUP.md` for details.

---

## Mission

VECTRA-PLAYER is a clean-slate refactor of REPLAYER focused on:
1. **Unified data storage** - DuckDB/Parquet as canonical truth + ChromaDB for vectors
2. **Server-authoritative state** - Trust server in live mode, eliminate local calculations
3. **RAG integration** - ChromaDB powers `rugs-expert` agent and Protocol Explorer UI
4. **Technical debt cleanup** - Remove deprecated code, eliminate hardcoded paths

**Core Principle:** Parquet is canonical truth; vector indexes are derived and rebuildable.

**December 20, 2025:** Standardized on **ChromaDB** (VectorDB) to reuse existing claude-flow infrastructure (~600 LOC). ChromaDB MCP server available for Claude Code integration.

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

### Event Schema (v2.0.0)

**DocTypes:**
| DocType | Purpose |
|---------|---------|
| `ws_event` | Raw WebSocket events |
| `game_tick` | Price/tick stream |
| `player_action` | Our button presses (human/bot) with full context |
| `other_player` | Other players' trades (from newTrade broadcast) |
| `server_state` | Server-authoritative snapshots (playerUpdate) |
| `system_event` | Connection/disconnect/errors |
| `alert_trigger` | Toast notification triggers |
| `ml_episode` | RL episode boundaries |
| `bbc_round` | Bull/Bear/Crab sidegame (placeholder) |
| `candleflip` | Candleflip sidegame (placeholder) |
| `short_position` | Short position tracking (placeholder) |

**Latency Tracking Chain:**
```
client_ts → server_ts → confirmed_ts
     ↓          ↓            ↓
send_latency  confirm_latency  total_latency (for bot timing)
```

**Full Schema Design:** `docs/plans/2025-12-23-expanded-event-schema-design.md`

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
| 12D | ✅ COMPLETE | System validation & legacy consolidation |
| Schema v2.0.0 | ✅ COMPLETE | Expanded schema design (#136) |
| Legacy Cleanup | 🔄 IN PROGRESS | Delete legacy recorders (#137) |
| 12E | ⏳ PENDING | Protocol Explorer UI |

### Schema v2.0.0 (Dec 23, 2025)
- ✅ #136 Architecture decision: EventStore is canonical
- ✅ `player_action` schema with full latency tracking
- ✅ `other_player` schema for ML training data
- ✅ `alert_trigger` schema with 25+ alert types
- ✅ Sidegame placeholders: BBC, Candleflip, Shorts
- 🔄 Legacy recorder deletion in progress (#137)

### Legacy Recorders (BEING REMOVED)
These files are deprecated and being deleted:
- `core/demo_recorder.py` → Replaced by `player_action` schema
- `core/recorder_sink.py` → Replaced by EventStore
- `services/unified_recorder.py` → Replaced by EventStore
- `debug/raw_capture_recorder.py` → No longer needed

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
| **Schema v2.0.0 Design** | `docs/plans/2025-12-23-expanded-event-schema-design.md` |
| Migration Guide | `docs/MIGRATION_GUIDE.md` |
| Phase 12D Plan | `docs/plans/2025-12-21-phase-12d-system-validation-and-legacy-consolidation.md` |
| Storage Migration Plan | `sandbox/duckdb_parquet_vectordb_migration_plan.md` |
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

*December 23, 2025 | Schema v2.0.0 - Legacy Cleanup In Progress*
