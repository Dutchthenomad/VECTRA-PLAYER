# Cross-Repository Coordination Plan

**Status:** Active
**Created:** December 18, 2025
**Purpose:** Coordinate development across VECTRA-PLAYER, claude-flow, and rugs-rl-bot

---

## Repository Overview

| Repository | Purpose | Owner |
|------------|---------|-------|
| **VECTRA-PLAYER** | Data capture, storage, UI | This repo |
| **claude-flow** | Dev orchestration, RAG, `rugs-expert` agent | Separate |
| **rugs-rl-bot** | ML training, RL environment | Separate |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐                                                     │
│  │  rugs.fun       │                                                     │
│  │  WebSocket      │                                                     │
│  └────────┬────────┘                                                     │
│           │                                                              │
│           ▼                                                              │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │              VECTRA-PLAYER                               │            │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │            │
│  │  │ WebSocket   │───▶│ EventStore  │───▶│  Parquet    │  │            │
│  │  │ Feed        │    │ (writer)    │    │  (DuckDB)   │  │            │
│  │  └─────────────┘    └─────────────┘    └──────┬──────┘  │            │
│  │                                               │          │            │
│  └───────────────────────────────────────────────┼──────────┘            │
│                                                  │                       │
│           ┌──────────────────────────────────────┤                       │
│           │                                      │                       │
│           ▼                                      ▼                       │
│  ┌─────────────────────────┐        ┌─────────────────────────┐         │
│  │      claude-flow        │        │      rugs-rl-bot        │         │
│  │  ┌─────────────────┐    │        │  ┌─────────────────┐    │         │
│  │  │ ChromaDB Vector │◀───┼────────┼──│ Parquet Reader  │    │         │
│  │  │ Index           │    │        │  │ (training data) │    │         │
│  │  └────────┬────────┘    │        │  └─────────────────┘    │         │
│  │           │             │        │                         │         │
│  │           ▼             │        │                         │         │
│  │  ┌─────────────────┐    │        │                         │         │
│  │  │ rugs-expert     │    │        │                         │         │
│  │  │ agent           │    │        │                         │         │
│  │  └─────────────────┘    │        │                         │         │
│  └─────────────────────────┘        └─────────────────────────┘         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. VECTRA-PLAYER → claude-flow

**What:** ChromaDB vector index built from Parquet data + protocol documentation

**Interface:**
```
~/rugs_data/
├── events_parquet/     # VECTRA-PLAYER writes (canonical game data)
├── vectors/            # Reserved for future use
└── manifests/
    └── schema_version.json  # Shared schema contract

claude-flow/
└── rag-pipeline/
    └── storage/chroma/  # ChromaDB index (claude-flow owns)
```

**Architecture:**
- VECTRA-PLAYER only writes Parquet (data producer)
- claude-flow owns vector indexing via ChromaDB (index builder)
- Rebuild command: `cd claude-flow/rag-pipeline && python -m ingestion.ingest`

**Decision:** claude-flow owns vector indexing with ChromaDB

**Coordination Required:**
- [x] Agree on `RUGS_DATA_DIR` location (`~/rugs_data/`) ✅
- [x] Define chunking strategy for `rugs-expert` queries ✅ (512 tokens, 50 overlap)
- [x] Document embedding model (`all-MiniLM-L6-v2`) ✅

---

### 2. VECTRA-PLAYER → rugs-rl-bot

**What:** ML training data from Parquet

**Interface:**
```python
# rugs-rl-bot reads VECTRA-PLAYER's Parquet directly
import duckdb

conn = duckdb.connect()
df = conn.execute("""
    SELECT * FROM '~/rugs_data/events_parquet/doc_type=game_tick/**/*.parquet'
    WHERE game_id = ?
    ORDER BY tick
""", [game_id]).df()
```

**Coordination Required:**
- [ ] Agree on schema for `game_tick` events
- [ ] Define feature engineering queries (DuckDB SQL)
- [ ] Ensure tick-by-tick data is complete (no gaps)

---

### 3. claude-flow `rugs-expert` → VECTRA-PLAYER

**What:** Protocol knowledge for validation

**Use Cases:**
1. VECTRA-PLAYER asks `rugs-expert`: "What fields are in playerUpdate?"
2. VECTRA-PLAYER validates captured data against spec
3. Schema drift detection

**Interface:**
```bash
# VECTRA-PLAYER can query rugs-expert via claude-flow
claude-flow agent rugs-expert "What fields are in gameStateUpdate.leaderboard?"
```

**Coordination Required:**
- [ ] Ensure `rugs-expert` knowledge base is up-to-date
- [ ] Define validation workflow for new events
- [ ] Document correction process for schema errors

---

## Shared Configuration

### Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `RUGS_DATA_DIR` | `~/rugs_data/` | VECTRA-PLAYER, claude-flow, rugs-rl-bot |
| `RUGS_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | claude-flow |
| `RUGS_SCHEMA_VERSION` | `1.0.0` | All |

### Schema Version Contract

All repos must agree on schema version:
```
~/rugs_data/manifests/schema_version.json
{
    "version": "1.0.0",
    "embedding_model": "all-MiniLM-L6-v2",
    "last_updated": "2025-12-18T00:00:00Z"
}
```

**Version Bump Rules:**
1. **Patch (1.0.x):** New optional fields, backward compatible
2. **Minor (1.x.0):** New required fields, migration needed
3. **Major (x.0.0):** Breaking changes, full rebuild required

---

## Development Workflow

### Adding a New Event Type

1. **VECTRA-PLAYER:** Add Pydantic model in `src/models/events/`
2. **VECTRA-PLAYER:** Update EventStore schema
3. **claude-flow:** Update `rugs-expert` knowledge base
4. **claude-flow:** Rebuild LanceDB index
5. **rugs-rl-bot:** Update feature engineering if needed

### Schema Validation Workflow

```
1. VECTRA-PLAYER captures new event
2. EventStore validates against schema
3. If unknown fields:
   a. Log to `manifests/unknown_fields.json`
   b. Alert for human review
   c. Query rugs-expert for field definition
4. If validated:
   a. Add to Pydantic model
   b. Update WEBSOCKET_EVENTS_SPEC.md
   c. Notify claude-flow to rebuild index
```

---

## Communication Channels

### Async Coordination

- **GitHub Issues:** Cross-reference issues with `[cross-repo]` prefix
- **Commit Messages:** Reference related issues in other repos

### Sync Points

| Event | Action |
|-------|--------|
| Schema version bump | All repos update dependency |
| New event type added | Update all three repos |
| Embedding model change | Rebuild all vector indexes |
| Breaking change | Major version bump, coordinated release |

---

## Current Status

### VECTRA-PLAYER

- [x] EventStore writes Parquet
- [x] DuckDB query layer
- [ ] Expand gameStateUpdate capture (9 → 50+ fields)
- [ ] LiveStateProvider (server-authoritative)

### claude-flow

- [x] `rugs-expert` agent exists
- [x] Canonical WEBSOCKET_EVENTS_SPEC.md established
- [x] ChromaDB RAG pipeline functional (211 chunks indexed)
- [ ] CONTEXT.md enforcement hooks
- [ ] Integration with VECTRA-PLAYER Parquet data (Phase 2)

### rugs-rl-bot

- [x] Can read JSONL recordings
- [ ] Update to read Parquet directly
- [ ] Feature engineering via DuckDB

---

## Action Items

| Task | Owner | Blocking |
|------|-------|----------|
| Finalize `RUGS_DATA_DIR` location | VECTRA-PLAYER | All |
| Define chunking strategy | claude-flow | rugs-expert |
| Expand gameStateUpdate capture | VECTRA-PLAYER | ML training quality |
| Update rugs-rl-bot to read Parquet | rugs-rl-bot | Training pipeline |
| Add schema validation workflow | VECTRA-PLAYER | Data quality |

---

*Last Updated: December 18, 2025*
