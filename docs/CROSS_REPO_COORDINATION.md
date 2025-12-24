# Cross-Repository Coordination

**Status:** Active
**Updated:** December 24, 2025

This document describes how VECTRA-PLAYER integrates with other repositories in the Rugs.fun ecosystem.

---

## Repository Ownership Matrix

| Repository | Location | **Primary Responsibility** |
|------------|----------|---------------------------|
| **VECTRA-PLAYER** | `/home/nomad/Desktop/VECTRA-PLAYER/` | Data capture, EventStore, UI, Parquet writing |
| **claude-flow** | `/home/nomad/Desktop/claude-flow/` | RAG pipeline, knowledge base, agents, ChromaDB |
| **rugs-rl-bot** | `/home/nomad/Desktop/rugs-rl-bot/` | ML training, RL bot, predictive models |
| **Data Directory** | `~/rugs_data/` | Canonical storage (Parquet) |

### Ownership Boundaries (IMPORTANT)

| Concern | Owner | Location |
|---------|-------|----------|
| WebSocket capture | VECTRA-PLAYER | `src/sources/` |
| Event persistence | VECTRA-PLAYER | `src/services/event_store/` |
| Parquet files | VECTRA-PLAYER | `~/rugs_data/events_parquet/` |
| **Knowledge base** | **claude-flow** | `knowledge/rugs-events/` |
| **RAG agents** | **claude-flow** | `agents/rugs-expert.md` |
| **ChromaDB vectors** | **claude-flow** | `rag-pipeline/storage/chroma/` |
| **Protocol documentation** | **claude-flow** | `knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` |
| **Empirical validation staging** | **claude-flow** | `knowledge/rugs-events/staging/` |
| ML models | rugs-rl-bot | `models/` |
| RL environment | rugs-rl-bot | `rugs_bot/env/` |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VECTRA-PLAYER                                │
│  (Data Capture & UI - NO RAG responsibility)                       │
│                                                                     │
│  WebSocket ──► EventBus ──► EventStoreService ──► Parquet Files    │
│      │                                               │              │
│      ▼                                               ▼              │
│  Live UI Display                       ~/rugs_data/events_parquet/  │
│                                                      │              │
└──────────────────────────────────────────────────────┼──────────────┘
                                                       │
        ┌──────────────────────────────────────────────┼──────────────┐
        │                                              │              │
        ▼                                              ▼              │
┌───────────────────────────────────┐      ┌──────────────────────────┐
│           claude-flow             │      │       rugs-rl-bot        │
│    (RAG & Knowledge OWNER)        │      │                          │
│                                   │      │  SidebetPredictor        │
│  knowledge/rugs-events/           │◄─────│  RL Environment          │
│    ├── WEBSOCKET_EVENTS_SPEC.md   │Query │  Training Scripts        │
│    ├── staging/                   │Parquet                          │
│    └── captures/                  │      └──────────────────────────┘
│                                   │
│  rag-pipeline/                    │
│    └── storage/chroma/            │
│                                   │
│  agents/rugs-expert.md            │
└───────────────────────────────────┘
```

---

## Responsibility Details

### VECTRA-PLAYER Responsibilities

**OWNS:**
- WebSocket connection and event capture
- EventBus pub/sub system
- EventStoreService → Parquet persistence
- UI (Tkinter main window, panels)
- Live state tracking
- Bot action execution (future)

**DOES NOT OWN:**
- ❌ Protocol documentation (→ claude-flow)
- ❌ RAG/vector indexing (→ claude-flow)
- ❌ Knowledge base maintenance (→ claude-flow)
- ❌ Agent definitions (→ claude-flow)

### claude-flow Responsibilities

**OWNS:**
- `rugs-expert` agent definition and behavior
- ChromaDB vector store for semantic search
- Protocol knowledge base (`knowledge/rugs-events/`)
- Strategy knowledge base (`knowledge/rugs-strategy/`)
- Empirical validation staging and ingestion
- RAG pipeline (ingestion, chunking, retrieval)
- CANONICAL PROMOTION LAWS enforcement

**Key Locations:**
```
claude-flow/
├── agents/rugs-expert.md                    # Agent definition
├── knowledge/
│   ├── rugs-events/
│   │   ├── WEBSOCKET_EVENTS_SPEC.md         # Canonical protocol spec
│   │   ├── CONTEXT.md                        # Promotion laws
│   │   ├── staging/                          # Pre-ingestion staging
│   │   │   └── 2025-12-24-empirical-validation/
│   │   └── captures/                         # Archived captures
│   └── rugs-strategy/
│       ├── L1-game-mechanics/
│       ├── L2-protocol/
│       │   └── confirmation-mapping.md       # Action→Event mapping
│       └── L7-advanced-analytics/
└── rag-pipeline/
    ├── ingestion/                            # Chunking & indexing
    ├── retrieval/                            # Query interface
    └── storage/chroma/                       # ChromaDB database
```

### rugs-rl-bot Responsibilities

**OWNS:**
- SidebetPredictor model
- RL trading bot (Gymnasium environment)
- Feature engineering
- Training scripts
- Model evaluation

**CONSUMES:**
- Parquet data from `~/rugs_data/`
- Protocol knowledge from claude-flow (for schema understanding)

---

## Integration Workflows

### 1. Empirical Validation Workflow

**When capturing new protocol data:**

1. **VECTRA-PLAYER** or manual CDP capture → JSONL raw capture
2. **Human** moves capture to claude-flow staging:
   ```bash
   mv /tmp/claude/capture.jsonl \
      ~/Desktop/claude-flow/knowledge/rugs-events/staging/YYYY-MM-DD-description/
   ```
3. **claude-flow** runs analysis:
   ```bash
   # Invoke rugs-expert agent to analyze
   # Creates analysis docs in staging/
   ```
4. **Human** reviews findings, approves CANONICAL promotion
5. **claude-flow** updates `WEBSOCKET_EVENTS_SPEC.md`
6. **claude-flow** runs ChromaDB ingestion:
   ```bash
   cd ~/Desktop/claude-flow/rag-pipeline
   python -m ingestion.ingest --collection rugs_events --source ../knowledge/rugs-events/
   ```

### 2. New Event Discovery Workflow

```
VECTRA-PLAYER captures event  →  Save raw to Parquet
                                        ↓
Human notices unknown event  →  Create staging folder in claude-flow
                                        ↓
rugs-expert agent analyzes   →  Generates analysis docs
                                        ↓
Human approves promotion     →  Update WEBSOCKET_EVENTS_SPEC.md
                                        ↓
ChromaDB ingestion           →  rugs-expert can now answer queries
```

### 3. Schema Change Workflow

1. **VECTRA-PLAYER** updates `src/services/event_store/schema.py`
2. **VECTRA-PLAYER** updates `docs/specs/` (local copy for reference)
3. **claude-flow** updates canonical `WEBSOCKET_EVENTS_SPEC.md`
4. **claude-flow** re-runs ChromaDB ingestion
5. Notify **rugs-rl-bot** if ML features affected

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUGS_DATA_DIR` | `~/rugs_data` | Base directory for Parquet data |

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
  "version": "2.0.0",
  "created": "2025-12-23T00:00:00Z",
  "fields": ["ts", "source", "doc_type", ...]
}
```

---

## Coordination Checklist

### When Adding New Event Types

1. ✅ VECTRA-PLAYER: Update `src/services/event_store/schema.py`
2. ✅ VECTRA-PLAYER: Add EventBus subscription
3. ✅ **claude-flow**: Update `WEBSOCKET_EVENTS_SPEC.md` (CANONICAL)
4. ✅ **claude-flow**: Run ChromaDB ingestion
5. ✅ Notify rugs-rl-bot if affects ML features

### When Changing Schema

1. Increment schema version in VECTRA-PLAYER
2. Add migration script if needed
3. Update claude-flow knowledge base
4. Update rugs-rl-bot consumers
5. Test backward compatibility

### When Running Empirical Validation

1. Capture via CDP (VECTRA-PLAYER or manual script)
2. Stage in **claude-flow** `knowledge/rugs-events/staging/`
3. Run rugs-expert analysis
4. Human review and approval
5. Promote to CANONICAL in claude-flow
6. Run ChromaDB ingestion

---

## Contact Points

| Issue Type | Repository |
|------------|------------|
| Data capture, UI, EventStore | VECTRA-PLAYER |
| RAG queries, agent behavior, knowledge base | **claude-flow** |
| Protocol documentation, event specs | **claude-flow** |
| ML training, RL environment | rugs-rl-bot |

---

*Last updated: December 24, 2025*
