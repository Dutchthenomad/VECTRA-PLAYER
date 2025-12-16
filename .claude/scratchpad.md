# VECTRA-PLAYER Session Scratchpad

Last Updated: 2025-12-16 00:30

---

## Quick Start for Fresh Sessions

```bash
# Read key context files
Read the following files:
1. /home/nomad/Desktop/VECTRA-PLAYER/CLAUDE.md
2. /home/nomad/Desktop/VECTRA-PLAYER/docs/plans/2025-12-15-canonical-database-design.md
3. /home/nomad/Desktop/VECTRA-PLAYER/src/models/events/CONTEXT.md

# Run tests (VECTRA-PLAYER has its own venv now)
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_models/ -v --tb=short

# Check GitHub issues
gh issue list --repo Dutchthenomad/VECTRA-PLAYER
```

---

## Active Work

### Current Phase: Phase 12 - Unified Data Architecture

**Mission:** Clean-slate refactor from REPLAYER with:
1. Unified data storage (DuckDB/Parquet as canonical truth + LanceDB vectors)
2. Server-authoritative state (trust socket feed)
3. RAG integration (LanceDB powers rugs-expert agent)
4. Technical debt cleanup (remove deprecated code)

### Phase 12A: Event Schemas - COMPLETE ✅

All 8 event schemas defined with 58 tests passing:

| Issue | Event | Status | Tests |
|-------|-------|--------|-------|
| #1 | GameStateUpdate | ✅ | 20 |
| #2 | PlayerUpdate | ✅ | 15 |
| #3 | UsernameStatus | ✅ | 3 |
| #4 | PlayerLeaderboardPosition | ✅ | 3 |
| #5 | NewTrade | ✅ | 2 |
| #6 | SidebetRequest/Response | ✅ | 4 |
| #7 | BuyOrder/SellOrder | ✅ | 4 |
| #8 | SystemEvents | ✅ | 6 |

**Commit:** `86de4a7` - `feat(schema): Add Phase 12A event schemas (Issues #1-8)`

---

## Next Steps: Phase 12B - Storage Layer

1. [ ] **Issue #9**: Parquet writer with buffering
   - Atomic writes, 100 events or 5 seconds
   - Partition by doc_type/date

2. [ ] **Issue #10**: DuckDB query layer
   - Use MCP MotherDuck server when available
   - Query helpers for common operations

3. [ ] **Issue #11**: Ingestion pipeline
   - EventBus subscription
   - Schema validation via Pydantic models
   - Error handling

---

## Key Design Decisions

1. **Decimal for all money/prices** - Prevents float precision drift
2. **Parquet is canonical truth** - Vector indexes are derived and rebuildable
3. **Partition by doc_type/date** - NOT by game_id (too many small files)
4. **Extra='allow' in Pydantic** - Forward compatibility with new server fields
5. **CONTEXT.md documentation** - Sister files to scripts, indexed to LanceDB
6. **meta_* prefix for ingestion fields** - `meta_ts`, `meta_seq`, `meta_source`

---

## Data Directory Structure

```
~/rugs_data/                          # RUGS_DATA_DIR (env var)
├── events_parquet/                   # Canonical truth store
│   ├── doc_type=ws_event/
│   ├── doc_type=game_tick/
│   ├── doc_type=player_action/
│   ├── doc_type=server_state/
│   └── doc_type=system_event/
├── vectors/                          # Derived LanceDB index
│   ├── events.lance/                 # WebSocket events ONLY
│   ├── code_context.lance/           # CONTEXT.md files ONLY
│   └── debug_notes.lance/            # AI reasoning ONLY
└── manifests/
    ├── schema_version.json
    └── vector_index_checkpoint.json
```

---

## GitHub Repo

**URL:** https://github.com/Dutchthenomad/VECTRA-PLAYER
**Branch:** main
**Latest commit:** `86de4a7`

### Staged Issues (Phase 12A)
- #1-8: Event schemas (COMPLETED in commit 86de4a7)

### TODO: Create Issues for Phase 12B-C
- #9-11: Storage layer (Parquet, DuckDB, Ingestion)
- #12-14: Vector DB (LanceDB tables)
- #15-16: DevOps (CONTEXT.md hooks, /context command)

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/plans/2025-12-15-canonical-database-design.md` | Master design document |
| `src/models/events/` | Pydantic schemas (Issues #1-8) |
| `src/services/event_store/` | EventStore skeleton |
| `docs/specs/WEBSOCKET_EVENTS_SPEC.md` | WebSocket protocol spec |

---

## Commands

```bash
# Run event schema tests
cd /home/nomad/Desktop/VECTRA-PLAYER/src
../.venv/bin/python -m pytest tests/test_models/ -v --tb=short

# View GitHub issues
gh issue list --repo Dutchthenomad/VECTRA-PLAYER

# DuckDB query (once Parquet files exist)
import duckdb
conn = duckdb.connect()
df = conn.execute("SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet' LIMIT 10").df()
```

---

## MCP Server Status

| Server | Purpose | Status |
|--------|---------|--------|
| mcp-server-motherduck | DuckDB cloud | Configured (needs testing) |
| mcp-lance-db | Vector search | Configured (needs testing) |
| mcp-chroma | Legacy RAG | Configured |

**Note:** Use MotherDuck MCP for DuckDB operations when available.

---

## Related Projects

| Project | Location | Purpose |
|---------|----------|---------|
| REPLAYER | `/home/nomad/Desktop/REPLAYER/` | Production system (Phase 11) |
| rugs-rl-bot | `/home/nomad/Desktop/rugs-rl-bot/` | RL training |
| claude-flow | `/home/nomad/Desktop/claude-flow/` | DevOps layer |
| Recordings | `/home/nomad/rugs_recordings/` | 929 games |

---

## Session History

- **2025-12-16**: Phase 12A complete (58 tests), pushed to GitHub
- **2025-12-15**: VECTRA-PLAYER forked from REPLAYER
- **2025-12-15**: Canonical database design document written
- **2025-12-15**: All 8 event schemas (Issues #1-8) implemented
