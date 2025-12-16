# REPLAYER Phase 12 - Unified Data Architecture & UI Refactor

**Status:** Approved Design (Cross-Session Coordination)
**Date:** December 15, 2025
**Authors:** Claude Opus (UI/WebSocket Session) + Claude (Storage/RAG Session)
**Stakeholder:** Dutch

---

## 1. Executive Summary

REPLAYER is undergoing a major architectural refactor to:
1. **Unify data storage** - Replace scattered JSON/JSONL captures with Parquet (DuckDB) + LanceDB
2. **Simplify live state** - Server-authoritative state replaces local calculations
3. **Enable semantic search** - LanceDB powers both `rugs-expert` agent and Protocol Explorer UI
4. **Clean up technical debt** - Remove stale/deprecated code, eliminate hardcoded paths

**Core Principle:** Parquet is the canonical truth store; vector indexes are derived and rebuildable.

---

## 2. Confirmed Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data root | `~/rugs_data/` | Clean break, survives repo changes |
| Vector store | LanceDB | Columnar + vector-native, metadata filtering |
| Embedding model | `all-MiniLM-L6-v2` (local) | Fast, claude-flow compatible; API models later |
| Retention | Keep forever + pruning CLI | Storage is cheap; add pruning when needed |
| Schema versioning | Manifest version bump | Rebuild vectors on version change |
| Live state | Server-authoritative | Trust server in live mode; local only for replay |

---

## 3. Target Architecture

### 3.1 Directory Structure

```
~/rugs_data/                          # RUGS_DATA_DIR (env var)
├── CONTEXT.md                        # Future AI reference doc
├── events_parquet/                   # Canonical truth store
│   ├── doc_type=ws_event/
│   │   └── date=2025-12-15/
│   │       └── part-0001.parquet
│   ├── doc_type=game_tick/
│   ├── doc_type=player_action/
│   ├── doc_type=server_state/
│   └── doc_type=system_event/
├── vectors/                          # Derived LanceDB index
│   └── events.lance/
├── exports/                          # Optional JSONL exports
└── manifests/
    ├── schema_version.json           # Current schema + embedding model
    └── vector_index_checkpoint.json  # Last indexed parquet file
```

### 3.2 Data Flow (Unified)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED DATA FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │ CDP Events  │  │ WebSocket   │  │ UI Actions  │                         │
│  │ (browser)   │  │ (public)    │  │ (trades)    │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                │                │                                 │
│         └────────────────┼────────────────┘                                 │
│                          ▼                                                  │
│                    ┌───────────┐                                            │
│                    │ EventBus  │ (existing pub/sub)                         │
│                    └─────┬─────┘                                            │
│                          │                                                  │
│         ┌────────────────┼────────────────┐                                 │
│         ▼                ▼                ▼                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │ EventStore  │  │ GameState   │  │    UI       │                         │
│  │ (writer)    │  │ (live=srv)  │  │ (display)   │                         │
│  └──────┬──────┘  └─────────────┘  └─────────────┘                         │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │  Parquet    │ ◄── Canonical Truth                                        │
│  │  (DuckDB)   │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼ (rebuild on demand)                                               │
│  ┌─────────────┐                                                            │
│  │  LanceDB    │ ◄── Derived Vector Index                                   │
│  │  (vectors)  │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ├──────────────────────────────┐                                    │
│         ▼                              ▼                                    │
│  ┌─────────────┐                ┌─────────────┐                             │
│  │rugs-expert  │                │ Protocol    │                             │
│  │   agent     │                │ Explorer UI │                             │
│  └─────────────┘                └─────────────┘                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Live vs Replay Mode

```
┌─────────────────────────────────────┬─────────────────────────────────────┐
│         LIVE MODE (CDP)             │         REPLAY MODE                 │
├─────────────────────────────────────┼─────────────────────────────────────┤
│                                     │                                     │
│  Server State ──▶ UI                │  Parquet/JSONL ──▶ Local Calc ──▶ UI│
│                                     │                                     │
│  • playerUpdate.cash = balance      │  • GameState tracks balance         │
│  • playerUpdate.positionQty = pos   │  • TradeManager calculates PNL      │
│  • playerUpdate.pnl = PNL           │  • Local state is truth             │
│                                     │                                     │
│  Server is TRUTH                    │  Local is TRUTH                     │
│  (no local calculations)            │  (no server available)              │
│                                     │                                     │
└─────────────────────────────────────┴─────────────────────────────────────┘
```

---

## 4. Schema Design

### 4.1 Canonical Event Envelope

All events share common columns plus type-specific fields:

```python
# Common columns (all doc_types)
@dataclass
class EventEnvelope:
    ts: datetime              # Event timestamp (UTC)
    source: str               # 'cdp' | 'public_ws' | 'replay' | 'ui'
    doc_type: str             # 'ws_event' | 'game_tick' | 'player_action' | etc.
    session_id: str           # Recording session UUID
    game_id: Optional[str]    # Game identifier (if applicable)
    player_id: Optional[str]  # Player DID (if applicable)
    username: Optional[str]   # Player username (if applicable)
    seq: int                  # Sequence number within session
    direction: str            # 'received' | 'sent'
    raw_json: str             # Full original payload (preserve fidelity)
```

### 4.2 Doc Types

| Doc Type | Source | Key Fields | Use Case |
|----------|--------|------------|----------|
| `ws_event` | CDP/WebSocket | `event_name`, `raw_json` | Protocol RAG, debugging |
| `game_tick` | gameStateUpdate | `tick`, `price`, `active`, `rugged` | Price history, ML training |
| `player_action` | UI/Bot | `action_type`, `amount`, `price` | Demo recording, imitation learning |
| `server_state` | playerUpdate | `cash`, `position_qty`, `avg_cost`, `pnl` | State verification, drift detection |
| `system_event` | Internal | `event_type`, `details` | Connection tracking, debugging |

### 4.3 Type-Specific Columns

```python
# game_tick specific
tick: int
price: Decimal
active: bool
rugged: bool
cooldown_timer: int
trade_count: int

# server_state specific (from playerUpdate)
cash: Decimal
position_qty: Decimal
avg_cost: Decimal
total_invested: Decimal
pnl: Decimal
pnl_percent: Decimal
has_active_trades: bool

# player_action specific
action_type: str  # 'BUY' | 'SELL' | 'SIDEBET' | 'PARTIAL_SELL'
amount: Decimal
price: Decimal
percentage: Optional[Decimal]  # For partial sells
```

---

## 5. Component Design

### 5.1 EventStore (New)

**Location:** `src/services/event_store/`

```
event_store/
├── __init__.py
├── writer.py          # Buffered Parquet writer
├── schema.py          # Pydantic models + version
├── reader.py          # DuckDB query helpers
├── paths.py           # All paths derived from RUGS_DATA_DIR
└── migrations.py      # Schema migration utilities
```

**Writer Interface:**
```python
class EventStoreWriter:
    def __init__(self, data_dir: Path = None):
        """Initialize with RUGS_DATA_DIR or default ~/rugs_data/"""

    def write(self, event: EventEnvelope) -> None:
        """Buffer event for batch write"""

    def flush(self) -> None:
        """Write buffered events to Parquet"""

    def close(self) -> None:
        """Flush and cleanup"""
```

**EventBus Subscription:**
```python
# In EventStore initialization
event_bus.subscribe(Events.WS_RAW_EVENT, self._handle_ws_event)
event_bus.subscribe(Events.GAME_TICK, self._handle_game_tick)
event_bus.subscribe(Events.PLAYER_UPDATE, self._handle_player_update)
event_bus.subscribe(Events.BOT_ACTION, self._handle_player_action)
event_bus.subscribe(Events.WS_SOURCE_CHANGED, self._handle_system_event)
```

### 5.2 VectorIndexer (New)

**Location:** `src/services/vector_indexer/`

```
vector_indexer/
├── __init__.py
├── indexer.py         # LanceDB index builder
├── chunker.py         # Event-to-chunk strategies
├── embedder.py        # Embedding model wrapper (local + API)
└── query.py           # Semantic search interface
```

**Indexer Interface:**
```python
class VectorIndexer:
    def __init__(self, data_dir: Path = None, model: str = "all-MiniLM-L6-v2"):
        """Initialize with embedding model"""

    def build_full(self) -> IndexStats:
        """Rebuild entire index from Parquet"""

    def build_incremental(self) -> IndexStats:
        """Index only new Parquet files since checkpoint"""

    def query(self, text: str, n: int = 10, filters: dict = None) -> List[SearchResult]:
        """Semantic search with optional metadata filters"""
```

**Chunking Strategy:**
```python
def chunk_ws_event(event: dict) -> str:
    """Format WebSocket event for embedding"""
    event_name = event.get('event_name', 'unknown')
    data = event.get('raw_json', '{}')

    # Event-specific formatting
    if event_name == 'gameStateUpdate':
        return f"Game tick event: tick={data.get('tickCount')}, price={data.get('price')}, active={data.get('active')}"
    elif event_name == 'playerUpdate':
        return f"Player state update: cash={data.get('cash')}, position={data.get('positionQty')}, pnl={data.get('cumulativePnL')}"
    # ... etc
```

**Future API Model Support:**
```python
class Embedder:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self.model_name = model
        if model.startswith("openai:"):
            self._init_openai(model.replace("openai:", ""))
        elif model.startswith("anthropic:"):
            self._init_anthropic(model.replace("anthropic:", ""))
        else:
            self._init_local(model)
```

### 5.3 LiveStateProvider (New)

**Location:** `src/services/live_state_provider.py`

Replaces local calculations when CDP is connected:

```python
class LiveStateProvider:
    """Provides server-authoritative state in live mode"""

    def __init__(self, event_bus):
        self._state = {}
        self._connected = False
        event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update)
        event_bus.subscribe(Events.WS_SOURCE_CHANGED, self._on_source_changed)

    @property
    def is_live(self) -> bool:
        return self._connected

    @property
    def balance(self) -> Optional[Decimal]:
        return self._state.get('cash') if self._connected else None

    @property
    def position_qty(self) -> Optional[Decimal]:
        return self._state.get('position_qty') if self._connected else None

    @property
    def pnl(self) -> Optional[Decimal]:
        return self._state.get('pnl') if self._connected else None
```

**UI Integration:**
```python
# In MainWindow tick handler
def _update_display(self, tick):
    if self.live_state.is_live:
        # Server-authoritative
        balance = self.live_state.balance
        position = self.live_state.position_qty
        pnl = self.live_state.pnl
    else:
        # Local calculations (replay mode)
        balance = self.state.get('balance')
        position = self.state.get('position')
        pnl = self._calculate_local_pnl()
```

### 5.4 Protocol Explorer UI (New)

**Location:** `src/ui/panels/protocol_explorer.py`

A new panel in REPLAYER for real-time event inspection:

```python
class ProtocolExplorerPanel:
    """
    Real-time WebSocket protocol explorer.

    Features:
    - Live event stream (color-coded by type)
    - Event schema browser (from LanceDB)
    - Sample viewer (representative examples)
    - Validation status (verified/unverified/needs-correction)
    """

    def __init__(self, parent, vector_indexer: VectorIndexer):
        self.indexer = vector_indexer
        # ... UI setup

    def show_event_schema(self, event_type: str):
        """Query LanceDB for event schema + samples"""
        results = self.indexer.query(
            f"event schema {event_type}",
            filters={"event_name": event_type}
        )
        # Display in schema viewer

    def mark_verified(self, event_type: str):
        """Mark event type as human-verified"""
        # Update metadata in LanceDB
```

---

## 6. Migration Plan

### Phase A: Dual-Write (Week 1)

**Goal:** New EventStore writes Parquet alongside existing recorders

**Tasks:**
1. Implement `EventStore` writer with Parquet output
2. Subscribe to EventBus events
3. Add `RUGS_DATA_DIR` config with `~/rugs_data/` default
4. Create `CONTEXT.md` in data root
5. Metrics: compare event counts between old/new systems

**Validation:**
- Both systems capture same events
- Parquet queryable via DuckDB
- No UI changes yet

### Phase B: Backfill + Vector Index (Week 2)

**Goal:** Import historical data, build LanceDB index

**Tasks:**
1. Backfill script: legacy JSONL → Parquet
2. Implement `VectorIndexer` with LanceDB
3. Implement chunking strategies per doc_type
4. Build initial index from backfilled data
5. CLI: `replayer index build` / `replayer index query "..."`

**Validation:**
- Historical games queryable in DuckDB
- Semantic search returns relevant events
- `rugs-expert` can answer protocol questions

### Phase C: Server-Authoritative State (Week 3)

**Goal:** UI shows server state in live mode

**Tasks:**
1. Implement `LiveStateProvider`
2. Refactor `MainWindow` to use provider
3. Remove local PNL calculations in live mode
4. Add "LIVE" indicator when server-authoritative
5. Protocol Explorer panel (basic version)

**Validation:**
- Live mode shows server balance/position/PNL
- Replay mode still uses local calculations
- No state drift in live mode

### Phase D: Cutover + Cleanup (Week 4)

**Goal:** Remove legacy systems, clean codebase

**Tasks:**
1. Disable legacy recorders via config flag
2. Remove `RecorderSink`, `DemoRecorderSink`, `RawCaptureRecorder`
3. Remove hardcoded paths (`~/rugs_recordings/`, `raw_captures/`, etc.)
4. Add JSONL export CLI for compatibility
5. Update all tests

**Hard Gates (must pass before deletion):**
- [ ] No module writes to filesystem except `EventStore`
- [ ] No hardcoded `/home/nomad/...` paths in runtime code
- [ ] No duplicate capture directories
- [ ] Tests enforce single writer pattern
- [ ] Schema version pinned in manifest

### Phase E: Protocol Explorer Full (Week 5)

**Goal:** Complete Protocol Explorer with validation workflow

**Tasks:**
1. Event schema browser with LanceDB queries
2. Sample viewer with live/historical examples
3. Validation status (verified/unverified)
4. CLI deep review tool
5. Corrections persist to manifest

---

## 7. CONTEXT.md Template

This file lives at `~/rugs_data/CONTEXT.md` for future AI reference:

```markdown
# RUGS Data Directory Context

**Purpose:** Canonical data store for REPLAYER game recordings and semantic index.

## Directory Structure

- `events_parquet/` - Canonical truth store (append-only Parquet)
- `vectors/` - Derived LanceDB index (rebuildable from Parquet)
- `exports/` - Optional JSONL exports for debugging
- `manifests/` - Schema version and index checkpoints

## Schema Version

Current: v1.0.0 (see `manifests/schema_version.json`)

## Key Principles

1. **Parquet is canonical** - Never modify; only append
2. **Vectors are derived** - Safe to delete and rebuild
3. **No hardcoded paths** - All paths derived from RUGS_DATA_DIR env var

## Rebuild Commands

```bash
# Rebuild vector index from Parquet
replayer index build --full

# Incremental index update
replayer index build --incremental

# Export to JSONL (for debugging)
replayer export --format jsonl --output ./debug_export/
```

## Modification Guidelines

- To add new doc_type: update `src/services/event_store/schema.py`, bump version
- To change embedding model: update manifest, run `replayer index build --full`
- To prune old data: (pruning CLI not yet implemented)

## Related Documentation

- Design doc: `REPLAYER/docs/plans/2025-12-15-phase-12-unified-data-architecture-design.md`
- WebSocket spec: `REPLAYER/docs/specs/WEBSOCKET_EVENTS_SPEC.md`
```

---

## 8. CLI Commands

```bash
# Data management
replayer data status              # Show data dir stats
replayer data export --format jsonl --output ./export/
replayer data prune --before 2025-01-01  # Future

# Vector index
replayer index build --full       # Rebuild entire index
replayer index build --incremental  # Index new data only
replayer index query "playerUpdate fields"  # Semantic search
replayer index stats              # Index statistics

# Schema
replayer schema show              # Current schema version
replayer schema migrate           # Run pending migrations

# Legacy compatibility
replayer legacy import ./old_recordings/  # Import legacy JSONL
replayer legacy export --format v1        # Export in old format
```

---

## 9. Testing Strategy

### Unit Tests
- `test_event_store_writer.py` - Parquet write/read cycle
- `test_vector_indexer.py` - Chunking, embedding, search
- `test_live_state_provider.py` - Server state handling
- `test_schema_migrations.py` - Version bump handling

### Integration Tests
- `test_eventbus_to_parquet.py` - Full event flow
- `test_parquet_to_lancedb.py` - Index rebuild
- `test_live_mode_e2e.py` - CDP → UI state display

### Guardrail Tests
- `test_no_hardcoded_paths.py` - Grep for forbidden patterns
- `test_single_writer.py` - Only EventStore writes to data dir
- `test_schema_version_pinned.py` - Manifest exists and valid

---

## 10. Dependencies

### New Dependencies
```
duckdb>=0.9.0          # Parquet query layer
lancedb>=0.3.0         # Vector store
sentence-transformers>=2.2.0  # Local embeddings
pyarrow>=14.0.0        # Parquet I/O
```

### Removed Dependencies (after cutover)
```
# None - ChromaDB was never fully integrated
```

---

## 11. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Dual-write phase, backfill validation, no deletion until verified |
| Performance regression | Background writer thread, batch flushes, async index updates |
| Breaking existing workflows | Legacy export CLI, config flag for dual-write |
| Embedding model changes | Model name in manifest, rebuild command documented |

---

## 12. Success Metrics

**Phase A Complete:**
- [ ] EventStore writes Parquet successfully
- [ ] Event counts match between old/new systems

**Phase B Complete:**
- [ ] Historical data backfilled
- [ ] `rugs-expert` answers "What fields are in playerUpdate?" correctly

**Phase C Complete:**
- [ ] Live mode shows server balance (not local calculation)
- [ ] No state drift warnings in live mode

**Phase D Complete:**
- [ ] Zero legacy recorders in codebase
- [ ] Zero hardcoded paths in runtime code

**Phase E Complete:**
- [ ] Protocol Explorer shows all 25+ event types
- [ ] Human can mark events as verified/unverified

---

## 13. Open Items for Future Phases

1. **API Embedding Models** - OpenAI/Anthropic embeddings for higher quality
2. **Retention/Pruning CLI** - Automated data lifecycle management
3. **Multi-Session Index** - Cross-session semantic search
4. **Training Dataset Export** - DuckDB → ML-ready format
5. **Real-Time Index Updates** - Stream to LanceDB without rebuild

---

*Document Version: 1.0.0*
*Last Updated: December 15, 2025*
*Next Review: After Phase A completion*
