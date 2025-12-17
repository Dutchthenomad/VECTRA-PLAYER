# Phase 12: Canonical Database Design

**Date:** December 15, 2025
**Status:** Approved
**GitHub Milestone:** Phase 12 - Unified Data Architecture

---

## Executive Summary

This document defines the canonical database architecture for VECTRA-PLAYER, establishing:
1. **Single source of truth** - DuckDB/Parquet for all WebSocket events
2. **Derived vector indexes** - LanceDB tables isolated by document type
3. **Server-authoritative state** - Trust socket feed, eliminate local calculations
4. **CONTEXT.md documentation** - Relationship-aware files as script siblings
5. **Professional DevOps** - GitHub Issues, PRs, claude-flow enforcement hooks

**Core Principle:** Parquet is canonical truth; vector indexes are derived and rebuildable.

---

## Section 1: Vector Database Isolation

### Three Isolated LanceDB Tables

```
~/rugs_data/vectors/
├── events.lance/          # WebSocket events ONLY
├── code_context.lance/    # CONTEXT.md files ONLY
└── debug_notes.lance/     # AI reasoning ONLY
```

### Rationale

| Table | Purpose | Prevents |
|-------|---------|----------|
| `events.lance` | Protocol documentation, event structure queries | Code comments polluting event semantics |
| `code_context.lance` | Module relationships, dependency graphs | Event data confusing code search |
| `debug_notes.lance` | AI reasoning, decision rationale | Historical noise in active debugging |

### Query Examples

```python
# Find events similar to "player balance update"
events_table.search("player balance update").limit(5).to_list()

# Find modules related to WebSocket parsing
code_context_table.search("websocket parsing").limit(5).to_list()

# Find why a design decision was made
debug_notes_table.search("why use Decimal for prices").limit(3).to_list()
```

---

## Section 2: Claude-Flow DevOps Integration

### Hook Configuration

**Location:** `/home/nomad/Desktop/claude-flow/hooks/`

```yaml
# context-enforcement.yaml
name: context_md_enforcement
trigger: pre_commit
scope: "*.py"
action: |
  # Check for CONTEXT.md sibling
  for py_file in $(git diff --cached --name-only | grep '\.py$'); do
    context_file="${py_file%.py}.CONTEXT.md"
    dir_context="$(dirname $py_file)/CONTEXT.md"
    if [[ ! -f "$context_file" && ! -f "$dir_context" ]]; then
      echo "ERROR: Missing CONTEXT.md for $py_file"
      exit 1
    fi
  done
```

### Auto-Generation Hook

```yaml
# context-stub-generator.yaml
name: context_stub_generator
trigger: file_create
scope: "*.py"
action: |
  # Generate CONTEXT.md stub for new Python files
  py_file="$1"
  context_file="$(dirname $py_file)/CONTEXT.md"
  if [[ ! -f "$context_file" ]]; then
    cat > "$context_file" << 'EOF'
  # $(basename $(dirname $py_file)) Context

  ## Purpose
  TODO: Describe module purpose.

  ## Related Scripts
  | Script | Relationship |
  |--------|--------------|
  | `TODO` | TODO |

  ## Data Flow
  TODO → this module → TODO

  ## Key Decisions
  TODO: Document design rationale.

  ## Status
  - [ ] Tests written
  - [ ] Indexed to LanceDB
  - [ ] Relationships verified
  EOF
  fi
```

### Session Start Hook

```yaml
# lancedb-index.yaml
name: lancedb_index_on_session
trigger: session_start
action: |
  # Index CONTEXT.md files to code_context.lance
  python3 -m vectra_player.index_contexts --table code_context
```

---

## Section 3: CONTEXT.md Template Structure

### Template

```markdown
# {module_name} Context

## Purpose
One sentence: what this module does.

## Related Scripts
| Script | Relationship |
|--------|--------------|
| `../event_bus.py` | Subscribes to events from |
| `./schema.py` | Imports EventEnvelope from |
| `../../ui/main_window.py` | Provides data to |

## Data Flow
```
[EventBus] → this module → [Parquet Writer]
                        → [LanceDB Indexer]
```

## Key Decisions
- **Why Parquet over SQLite:** Append-only, columnar, DuckDB-native
- **Why single writer:** Avoid race conditions, consistent ordering

## Status
- [x] Tests written
- [x] Indexed to LanceDB
- [ ] Relationships verified
```

### Relationship Types

| Relationship | Meaning |
|--------------|---------|
| `Imports X from` | Direct Python import |
| `Subscribes to events from` | EventBus subscriber |
| `Publishes events to` | EventBus publisher |
| `Provides data to` | Output consumer |
| `Receives data from` | Input source |
| `Inherits from` | Class inheritance |
| `Implements interface` | ABC implementation |

---

## Section 4: Canonical Event Schema (Pydantic)

### Common Envelope

All events share these metadata fields:

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class EventMetadata(BaseModel):
    """Metadata added during ingestion (not from socket)"""
    _ts: datetime              # Ingestion timestamp (UTC)
    _seq: int                  # Sequence number within session
    _source: Literal['cdp', 'public_ws', 'replay', 'ui']
    _session_id: str           # Recording session UUID
    _game_id: str | None       # Game identifier (if applicable)
```

### Event Types to Define (GitHub Issues #1-8)

| Issue | Event | Auth Required | Priority |
|-------|-------|---------------|----------|
| #1 | `gameStateUpdate` | No | P0 - Primary tick |
| #2 | `playerUpdate` | Yes | P0 - Server state |
| #3 | `usernameStatus` | Yes | P1 - Identity |
| #4 | `playerLeaderboardPosition` | Yes | P2 - Rank |
| #5 | `standard/newTrade` | No | P1 - Trade feed |
| #6 | `sidebetResponse` | Yes | P1 - Sidebet |
| #7 | `buyOrder/sellOrder` | Yes | P0 - Execution |
| #8 | System events | N/A | P1 - Lifecycle |

### Schema Design Principles

1. **Use Decimal for all money/prices** - Never float
2. **Preserve original field names** - Match socket payload exactly
3. **Add metadata prefix with underscore** - `_ts`, `_seq`, `_source`
4. **Nested models for complex fields** - `LeaderboardEntry`, `PartialPrice`
5. **Optional fields with defaults** - Handle partial payloads gracefully

---

## Section 5: GitHub Professional Workflow

### Milestone Structure

```
Phase 12A: Event Schemas (Issues #1-8)
├── #1 gameStateUpdate schema
├── #2 playerUpdate schema
├── #3 usernameStatus schema
├── #4 playerLeaderboardPosition schema
├── #5 standard/newTrade schema
├── #6 sidebetResponse schema
├── #7 buyOrder/sellOrder schema
└── #8 System event schemas

Phase 12B: Storage Layer (Issues #9-11)
├── #9 Parquet writer with buffering
├── #10 DuckDB query layer
└── #11 Ingestion pipeline (EventBus → Parquet)

Phase 12C: Vector DB + DevOps (Issues #12-16)
├── #12 LanceDB events table
├── #13 LanceDB code_context table
├── #14 LanceDB debug_notes table
├── #15 CONTEXT.md enforcement hooks
└── #16 /context command for claude-flow
```

### Branch Naming

```
feat/issue-{number}-{short-description}
fix/issue-{number}-{short-description}
docs/issue-{number}-{short-description}
```

### PR Template

```markdown
## Summary
Brief description of changes.

## Related Issue
Closes #{issue_number}

## Changes
- [ ] Schema defined in `src/models/events/`
- [ ] Tests added in `src/tests/test_models/`
- [ ] CONTEXT.md updated
- [ ] Indexed to LanceDB

## Testing
```bash
cd src && ../.venv/bin/python -m pytest tests/test_models/ -v
```
```

---

## Section 6: Parquet Partitioning Strategy

### Directory Structure

```
~/rugs_data/events_parquet/
├── doc_type=ws_event/
│   ├── date=2025-12-15/
│   │   ├── part-0001.parquet
│   │   └── part-0002.parquet
│   └── date=2025-12-16/
├── doc_type=game_tick/
│   └── date=2025-12-15/
├── doc_type=player_action/
│   └── date=2025-12-15/
├── doc_type=server_state/
│   └── date=2025-12-15/
└── doc_type=system_event/
    └── date=2025-12-15/
```

### Partitioning Rationale

| Partition Key | Why First/Second |
|---------------|------------------|
| `doc_type` | First - Most queries filter by event type |
| `date` | Second - Time-range queries, data lifecycle |
| ~~`game_id`~~ | NOT used - Too many small files (929+ games) |

### DuckDB Query Examples

```sql
-- All events for a specific game (uses doc_type partition)
SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE game_id = 'abc123';

-- Events in date range (uses both partitions)
SELECT * FROM '~/rugs_data/events_parquet/doc_type=game_tick/date=2025-12-15/*.parquet';

-- Cross-partition analytics
SELECT doc_type, COUNT(*)
FROM '~/rugs_data/events_parquet/**/*.parquet'
GROUP BY doc_type;
```

### MCP Integration: MotherDuck

**Requirement:** Use `mcp-server-motherduck` for DuckDB operations when available.

```python
# Check MCP availability
try:
    from mcp_motherduck import DuckDBClient
    db = DuckDBClient()  # Uses MCP server
except ImportError:
    import duckdb
    db = duckdb.connect()  # Fallback to local
```

**Benefits:**
- Cloud persistence of query results
- Shareable analytics dashboards
- Team collaboration on data exploration

---

## Section 7: MCP Server Configuration

### Required MCP Servers

| Server | Purpose | Status |
|--------|---------|--------|
| `mcp-server-motherduck` | DuckDB cloud queries | Configured (needs testing) |
| `mcp-lance-db` | Vector similarity search | Configured (needs testing) |
| `mcp-chroma` | Legacy RAG (migration source) | Configured |

### Configuration Location

```
~/.claude/settings.json  # MCP server definitions
```

### Initialization Check

```python
def check_mcp_servers():
    """Verify MCP servers are available."""
    servers = {
        'motherduck': 'mcp-server-motherduck',
        'lancedb': 'mcp-lance-db',
    }
    status = {}
    for name, server in servers.items():
        try:
            # Attempt connection
            status[name] = 'connected'
        except Exception as e:
            status[name] = f'failed: {e}'
    return status
```

---

## Implementation Order

### Phase 12A: Event Schemas (Week 1)

1. **Issue #1: gameStateUpdate** - Primary tick event
   - Define Pydantic model with all nested types
   - Add tests for parsing real payloads
   - Create CONTEXT.md for schema module

2. **Issue #2: playerUpdate** - Server-authoritative state
   - Critical for wallet balance, position tracking
   - Must match server payload exactly

3. **Issues #3-8:** Remaining event schemas

### Phase 12B: Storage Layer (Week 2)

4. **Issue #9: Parquet writer**
   - Buffered writes (100 events or 5 seconds)
   - Atomic file operations
   - Partition directory creation

5. **Issue #10: DuckDB query layer**
   - Helper functions for common queries
   - MCP MotherDuck integration

6. **Issue #11: Ingestion pipeline**
   - EventBus subscription
   - Schema validation
   - Error handling

### Phase 12C: Vector DB + DevOps (Week 3)

7. **Issues #12-14: LanceDB tables**
   - Embedding model selection
   - Table schema definitions
   - Incremental indexing

8. **Issues #15-16: DevOps**
   - Hook implementation
   - `/context` command

---

## Success Criteria

### Canonical Database Complete When:

- [ ] All 8 event schemas defined and tested (Issues #1-8)
- [ ] Parquet writer handles 100 events/sec without data loss
- [ ] DuckDB queries return correct results for all event types
- [ ] LanceDB similarity search finds relevant events
- [ ] CONTEXT.md exists for all new modules
- [ ] No direct filesystem writes except through EventStore

### Live Game Fidelity When:

- [ ] UI displays correct wallet balance from `playerUpdate`
- [ ] Position tracking matches server state exactly
- [ ] Trade execution reflects in UI within 1 second
- [ ] Human can play full game session through VECTRA-PLAYER UI

---

## References

- **WebSocket Events Spec:** `docs/specs/WEBSOCKET_EVENTS_SPEC.md`
- **Existing EventStore:** `src/services/event_store/`
- **Claude-Flow Hooks:** `/home/nomad/Desktop/claude-flow/hooks/`
- **Data Directory:** `~/rugs_data/`

---

*Approved: December 15, 2025*
