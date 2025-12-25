# WebSocket Debugging Workflow - Implementation Summary

**Date:** December 24, 2025
**Agent:** rugs-expert
**Status:** ✅ Production Ready

---

## What Was Delivered

A **complete persistent real-time WebSocket debugging workflow** for rugs.fun protocol observation.

**Key Insight:** VECTRA-PLAYER already has all infrastructure needed. No new tools required.

---

## Deliverables (6 Files)

### 1. Documentation (5 Files)

| File | Size | Purpose |
|------|------|---------|
| **DEBUGGING_README.md** | 12 KB | Master navigation document |
| **WEBSOCKET_DEBUGGING_WORKFLOW.md** | 8.3 KB | Complete workflow guide |
| **DEBUGGING_QUICKSTART.md** | 2.0 KB | 1-page quick reference |
| **RUGS_EXPERT_CHEATSHEET.md** | 9.4 KB | Query examples & templates |
| **DEBUGGING_TROUBLESHOOTING.md** | 11 KB | Common issues & fixes |

**Total Documentation:** ~42.7 KB across 5 markdown files

### 2. Automation Script (1 File)

| File | Size | Purpose |
|------|------|---------|
| **start_debugging.sh** | 3.0 KB | One-command workflow startup |

**Features:**
- Kills existing Chrome instances
- Starts Chrome with CDP on port 9222
- Launches VECTRA-PLAYER
- Verifies connections
- Provides next-step instructions

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  USER WORKFLOW                                            │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. ./start_debugging.sh                                 │
│     ↓                                                     │
│  2. Chrome (CDP port 9222) + VECTRA-PLAYER launch        │
│     ↓                                                     │
│  3. Menu → Browser → Connect to Live Browser             │
│     ↓                                                     │
│  4. Menu → Sources → Live WebSocket Feed                 │
│     ↓                                                     │
│  5. Play game in browser                                 │
│     ↓                                                     │
│  6. Events appear in real-time                           │
│     ↓                                                     │
│  7. Ask rugs-expert questions                            │
│     ↓                                                     │
│  8. Query EventStore with DuckDB                         │
│     ↓                                                     │
│  9. Document findings to canonical spec                  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Key Components Leveraged

**From VECTRA-PLAYER:**

1. **BrowserBridge** (`src/browser/bridge.py`)
   - CDP connection management
   - Multi-strategy button selectors
   - Async click queue

2. **CDPWebSocketInterceptor** (`src/sources/cdp_websocket_interceptor.py`)
   - WebSocket frame capture
   - Socket.IO parsing
   - Auth event support

3. **EventStore** (`src/services/event_store/`)
   - Parquet persistence
   - DuckDB queryable
   - Schema v2.0.0 support

4. **LiveStateProvider** (`src/services/live_state_provider.py`)
   - Server-authoritative state
   - Balance tracking
   - Position management

5. **WebSocketFeed** (`src/sources/websocket_feed.py`)
   - Real-time event parsing
   - Phase detection
   - Latency tracking

**From claude-flow:**

1. **ChromaDB RAG** (`rag-pipeline/`)
   - Vector indexing
   - Semantic search
   - Knowledge retrieval

2. **Canonical Spec** (`knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md`)
   - Single source of truth
   - Event schemas
   - Field definitions

---

## Workflow Capabilities

### 1. Real-Time Monitoring

**What:**
- Live WebSocket event display
- Price/tick updates
- Trade confirmations
- Balance changes

**How:**
- VECTRA-PLAYER live feed window
- EventBus pub/sub
- Tkinter UI updates

**Output:**
- Visual event log
- Automatic Parquet persistence

### 2. Continuous Conversation

**What:**
- Ask protocol questions while monitoring
- Get real-time event explanations
- Query historical data
- Debug issues interactively

**How:**
- rugs-expert agent (Claude Code)
- Natural language queries
- DuckDB integration
- ChromaDB RAG

**Output:**
- Authoritative answers
- Code examples
- Data analysis

### 3. Data Persistence

**What:**
- All events saved to Parquet
- DuckDB queryable
- ChromaDB indexed
- Exportable to JSONL

**How:**
- EventStore auto-buffering
- Atomic writes
- Schema versioning
- Partitioned storage

**Output:**
- `~/rugs_data/events_parquet/`
- Permanent record
- Replayable sessions

### 4. Protocol Documentation

**What:**
- Update canonical spec
- Add field definitions
- Document new events
- Validate schemas

**How:**
- rugs-expert verification
- User approval workflow
- ChromaDB re-indexing
- Version control

**Output:**
- Updated WEBSOCKET_EVENTS_SPEC.md
- Refreshed RAG index
- Knowledge base growth

---

## Quick Start Guide

### Step 1: Launch (30 seconds)

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER
./start_debugging.sh
```

**Output:**
- Chrome opens on rugs.fun
- VECTRA-PLAYER UI appears
- CDP verified at port 9222

### Step 2: Connect (30 seconds)

**In VECTRA-PLAYER UI:**
1. Menu → Browser → Connect to Live Browser
2. Wait for "🟢 Connected" status
3. Menu → Sources → Live WebSocket Feed

**Output:**
- Browser bridge connected
- WebSocket interception active
- Live feed window open

### Step 3: Play & Observe (continuous)

**In Chrome window:**
- Navigate to https://rugs.fun
- Connect wallet (Phantom)
- Play game normally

**In VECTRA-PLAYER window:**
- Watch events stream in real-time
- See gameStateUpdate, playerUpdate, etc.

**Output:**
- Events displayed live
- Saved to Parquet automatically

### Step 4: Query & Debug (as needed)

**Ask rugs-expert:**
```
"What fields are in playerUpdate?"
"Show me my last 5 trades"
"Why is my balance not updating?"
```

**Or query directly:**
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"
```

**Output:**
- Answers from canonical spec
- Real data examples
- Debugging insights

---

## Use Case Examples

### A. Event Discovery

**Scenario:** Unknown event appears

**Workflow:**
1. Observe event in live feed
2. Ask: "Explain the [eventName] event"
3. rugs-expert checks canonical spec
4. If not documented, extracts from EventStore
5. Proposes spec update
6. User approves
7. Spec updated + RAG re-indexed

**Result:** Protocol knowledge grows

### B. Button XPath Discovery

**Scenario:** Need selector for automation

**Workflow:**
1. Inspect button in Chrome DevTools
2. Ask: "What is the XPath for the SELL button?"
3. rugs-expert shows BrowserBridge strategies
4. Test selector in live browser
5. Validate with real click
6. Add to SelectorStrategy if new

**Result:** Reliable automation selectors

### C. Latency Profiling

**Scenario:** Trades feel slow

**Workflow:**
1. Execute 10 trades
2. Ask: "What is my average trade latency?"
3. rugs-expert queries buyOrder → buyOrderResponse
4. Calculates median, P95, P99
5. Identifies bottlenecks
6. Suggests optimizations

**Result:** Performance insights

### D. Balance Reconciliation

**Scenario:** UI shows wrong balance

**Workflow:**
1. Notice discrepancy
2. Ask: "What is my server balance?"
3. rugs-expert queries last playerUpdate
4. Compares to LiveStateProvider
5. Identifies sync issue
6. Suggests reconnection

**Result:** Issue diagnosed and fixed

---

## Data Storage Architecture

### Canonical Storage (Parquet)

```
~/rugs_data/events_parquet/
├── doc_type=ws_event/
│   └── session_20251224_150430.parquet   # Raw WebSocket events
├── doc_type=game_tick/
│   └── session_20251224_150430.parquet   # Parsed tick data
├── doc_type=player_action/
│   └── session_20251224_150430.parquet   # Your trades
└── doc_type=server_state/
    └── session_20251224_150430.parquet   # Server balance updates
```

**Characteristics:**
- Columnar format (fast queries)
- Compressed (efficient storage)
- Schema versioned
- DuckDB compatible

### Vector Index (ChromaDB)

```
~/Desktop/claude-flow/rag-pipeline/storage/chroma/
├── chroma.sqlite3              # Vector database
└── rugs_events/                # Collection
    ├── embeddings.bin
    └── metadata.json
```

**Characteristics:**
- Semantic search
- Fast retrieval
- Rebuildable from Parquet
- rugs-expert powered

---

## Query Interfaces

### 1. Natural Language (rugs-expert)

**Examples:**
```
"Show me the last 10 events"
"What fields are in playerUpdate?"
"Explain game phase detection"
"Why is my balance wrong?"
```

**Output:**
- Authoritative answers from canonical spec
- Real data examples from EventStore
- Code snippets when relevant
- Troubleshooting steps

### 2. SQL (DuckDB)

**Examples:**
```sql
-- Recent events
SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
ORDER BY timestamp DESC LIMIT 10

-- Event type distribution
SELECT data->>'event' as event, COUNT(*)
FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
GROUP BY event

-- Latency statistics
SELECT AVG(CAST(data->>'latency' as FLOAT))
FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE data->>'event' = 'gameStateUpdate'
```

**Output:**
- Raw query results
- Fast aggregations
- Time-series analysis

### 3. Vector Search (ChromaDB)

**Examples:**
```bash
cd ~/Desktop/claude-flow/rag-pipeline
python -m retrieval.retrieve "What fields are in playerUpdate?" -k 5
```

**Output:**
- Semantic matches
- Relevant documentation chunks
- Related events

---

## Troubleshooting Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| CDP not responding | `pkill chrome && ./start_debugging.sh` |
| No events captured | Refresh browser (F5) after connecting |
| Missing auth events | Check Phantom wallet connected |
| UI frozen | `pkill -f VECTRA-PLAYER && ./run.sh` |
| Balance mismatch | Reconnect browser in VECTRA-PLAYER |
| Disk full | `find ~/rugs_data -mtime +7 -delete` |
| Corrupted Parquet | Move to `~/rugs_data/quarantine/` |

**Full Guide:** See `DEBUGGING_TROUBLESHOOTING.md`

---

## Commands Cheat Sheet

### Start/Stop
```bash
./start_debugging.sh              # Start everything
pkill chrome && pkill -f VECTRA   # Stop everything
```

### Verify
```bash
curl -s http://localhost:9222/json/version | jq .Browser  # CDP OK?
ls -lht ~/rugs_data/events_parquet/doc_type=ws_event/     # Events captured?
```

### Query
```bash
# Last 10 events
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"

# Event count
duckdb -c "SELECT COUNT(*) FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'"
```

### Backup
```bash
tar -czf ~/rugs_data_backup_$(date +%Y%m%d).tar.gz ~/rugs_data/
```

---

## Integration Points

### VECTRA-PLAYER Integration

**Used Components:**
- BrowserBridge (CDP management)
- CDPWebSocketInterceptor (event capture)
- EventStore (persistence)
- LiveStateProvider (state sync)
- WebSocketFeed (parsing)

**Location:** `/home/nomad/Desktop/VECTRA-PLAYER/src/`

### claude-flow Integration

**Used Components:**
- ChromaDB RAG (semantic search)
- Canonical spec (protocol truth)
- Knowledge base (L1-L7 layers)

**Location:** `/home/nomad/Desktop/claude-flow/`

### rugs-expert Agent

**Capabilities:**
- Protocol knowledge specialist
- Real-time EventStore queries
- Button selector guidance
- Debugging support

**Access:** Claude Code conversations

---

## Success Metrics

### Functional Requirements ✅

- [x] Persistent WebSocket monitoring
- [x] Real-time event display
- [x] Continuous conversation support
- [x] Multi-window workflow (browser + VECTRA + Claude)
- [x] Data persistence (Parquet)
- [x] Query interface (DuckDB + NL)
- [x] Documentation system (RAG)

### Technical Requirements ✅

- [x] CDP connection stability
- [x] EventBus integration
- [x] Thread-safe UI updates
- [x] Atomic Parquet writes
- [x] Schema versioning
- [x] Error boundaries

### User Experience ✅

- [x] 2-minute quick start
- [x] One-command startup script
- [x] Clear troubleshooting guide
- [x] Example workflows
- [x] Cheat sheet reference
- [x] Master navigation doc

---

## Future Enhancements

### Potential Additions (Not Required)

1. **Real-Time Alerts**
   - Toast notifications on specific events
   - Configurable triggers
   - Sound alerts

2. **Event Filtering**
   - UI controls to show/hide event types
   - Search/filter live feed
   - Custom event groups

3. **Export Formats**
   - CSV export
   - JSON export
   - Parquet → SQLite

4. **Dashboard UI**
   - Metrics visualization
   - Latency graphs
   - Event frequency charts

5. **Multi-Session Comparison**
   - Side-by-side event logs
   - Diff tool
   - Performance comparison

**Note:** Current implementation is **production ready** without these.

---

## Maintenance

### Regular Tasks

**Daily:**
- No action required (auto-persist to Parquet)

**Weekly:**
- Check disk usage: `df -h ~/rugs_data`
- Verify EventStore integrity (DuckDB query test)

**Monthly:**
- Archive old sessions: `tar -czf ~/archive.tar.gz ~/rugs_data`
- Clean old data (>30 days): `find ~/rugs_data -mtime +30 -delete`

**On Protocol Updates:**
- Update canonical spec (with rugs-expert)
- Re-index ChromaDB: `python -m ingestion.ingest`
- Verify schema compatibility

### Documentation Updates

**When to Update:**
- New event discovered
- Button selector changed
- Workflow improved
- Issue resolution found

**How to Update:**
- Edit relevant markdown file
- Commit to version control
- Notify rugs-expert for RAG re-indexing

---

## Conclusion

**Delivered:** Complete persistent real-time WebSocket debugging workflow for rugs.fun

**Key Innovation:** Leverages existing VECTRA-PLAYER infrastructure - no new tools needed

**User Benefit:**
- Monitor protocol in real-time
- Continue conversations while observing
- Query historical data effortlessly
- Document findings systematically

**Status:** ✅ Production Ready - Start using immediately

---

## Quick Links

**Documentation:**
- [Master README](DEBUGGING_README.md) - Navigation hub
- [Quick Start](DEBUGGING_QUICKSTART.md) - 1-page reference
- [Full Workflow](WEBSOCKET_DEBUGGING_WORKFLOW.md) - Complete guide
- [Cheat Sheet](RUGS_EXPERT_CHEATSHEET.md) - Query examples
- [Troubleshooting](DEBUGGING_TROUBLESHOOTING.md) - Issue fixes

**Scripts:**
- `./start_debugging.sh` - One-command startup

**Data:**
- `~/rugs_data/events_parquet/` - Canonical storage
- `~/Desktop/claude-flow/rag-pipeline/storage/chroma/` - Vector index

**Knowledge Base:**
- `~/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` - Protocol spec
- `~/Desktop/claude-flow/knowledge/rugs-events/RUGS_BROWSER_CONNECTION.md` - CDP guide

---

**Implementation Date:** December 24, 2025
**Agent:** rugs-expert
**Status:** Production Ready
**Next Action:** Run `./start_debugging.sh` and start observing!
