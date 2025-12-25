# WebSocket Debugging Workflow - Complete Guide

**Purpose:** Real-time rugs.fun protocol observation and analysis
**Agent:** rugs-expert (Claude Code protocol specialist)
**Status:** Production Ready

---

## What Is This?

A **persistent real-time WebSocket debugging workflow** that lets you:

1. **Play rugs.fun** in a browser window
2. **Monitor WebSocket events** in real-time (VECTRA-PLAYER UI)
3. **Continue conversations** with rugs-expert while monitoring runs
4. **Query captured data** using DuckDB and natural language
5. **Document findings** to the protocol knowledge base

**No new tools needed** - everything is already built into VECTRA-PLAYER.

---

## Quick Start (2 Minutes)

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER

# 1. Start debugging workflow
./start_debugging.sh

# 2. In VECTRA-PLAYER UI:
#    Menu → Browser → Connect to Live Browser
#    Menu → Sources → Live WebSocket Feed

# 3. Play game in browser window
#    Events appear in real-time

# 4. Ask rugs-expert questions
#    "What fields are in playerUpdate?"
#    "Show me the last 10 events"
```

---

## Documentation Structure

| Document | Purpose | Audience |
|----------|---------|----------|
| **DEBUGGING_QUICKSTART.md** | 1-page quick reference | First-time users |
| **WEBSOCKET_DEBUGGING_WORKFLOW.md** | Complete workflow guide | All users |
| **RUGS_EXPERT_CHEATSHEET.md** | Query examples and templates | Developers |
| **DEBUGGING_TROUBLESHOOTING.md** | Common issues and fixes | Support |
| **DEBUGGING_README.md** (this) | Overview and navigation | Documentation hub |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR DESKTOP                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐       ┌──────────────┐                    │
│  │   Browser    │       │ VECTRA-PLAYER│                    │
│  │  (rugs.fun)  │ ────▶ │  Live Feed   │                    │
│  │              │  CDP  │  UI Display  │                    │
│  └──────────────┘       └──────────────┘                    │
│         │                       │                           │
│         │                       ▼                           │
│         │              ┌──────────────┐                     │
│         │              │  EventStore  │                     │
│         │              │  (Parquet)   │                     │
│         │              └──────────────┘                     │
│         │                       │                           │
│         │                       ▼                           │
│         │              ┌──────────────┐                     │
│         └────────────▶ │  rugs-expert │                     │
│                        │  (Claude)    │                     │
│                        └──────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**

1. **Chrome with CDP** - Browser connection on port 9222
2. **BrowserBridge** - CDP WebSocket interception
3. **WebSocketFeed** - Socket.IO event parsing
4. **EventStore** - Parquet persistence (~rugs_data/)
5. **LiveStateProvider** - Server-authoritative state
6. **rugs-expert** - Protocol knowledge specialist

---

## Workflow Overview

### Phase 1: Setup (2 minutes)

```bash
# Start Chrome + VECTRA-PLAYER
./start_debugging.sh

# Connect in UI
# Menu → Browser → Connect to Live Browser
```

### Phase 2: Monitor (continuous)

- Play game in browser
- Watch events in VECTRA-PLAYER live feed
- Events auto-saved to Parquet

### Phase 3: Query (as needed)

**Ask rugs-expert:**
- "What fields are in playerUpdate?"
- "Show me my last 5 trades"
- "Why is my balance not updating?"

**Or query directly:**
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"
```

### Phase 4: Document (on discovery)

**You:** "Found new field `rugProbability`"

**rugs-expert:**
1. Verifies in EventStore
2. Proposes spec update
3. Awaits approval
4. Updates canonical spec + re-indexes ChromaDB

---

## Use Cases

### 1. Event Discovery

**Goal:** Understand unknown event

```
1. Trigger action in game (e.g., place sidebet)
2. Observe events in live feed
3. Ask rugs-expert: "Explain the sidebetResponse event"
4. Review payload examples
5. Document in protocol spec
```

### 2. Button Automation

**Goal:** Find XPath for UI automation

```
1. Inspect button in Chrome DevTools
2. Ask: "What is the XPath for the SELL button?"
3. Test selector in BrowserBridge
4. Validate with real click
5. Add to SelectorStrategy
```

### 3. Latency Analysis

**Goal:** Profile trade execution speed

```
1. Execute several trades
2. Query buyOrder → buyOrderResponse pairs
3. Calculate latency distribution (median, P95, P99)
4. Identify bottlenecks
5. Optimize critical path
```

### 4. Balance Reconciliation

**Goal:** Debug UI/server mismatch

```
1. Notice balance discrepancy
2. Query last playerUpdate event
3. Check LiveStateProvider state
4. Identify sync issue
5. Force reconnection to fix
```

---

## Data Storage

### Canonical Storage (Parquet)

```
~/rugs_data/events_parquet/
├── doc_type=ws_event/       # Raw WebSocket events
├── doc_type=game_tick/      # Parsed tick data
├── doc_type=player_action/  # Your trades/actions
└── doc_type=server_state/   # Server balance updates
```

### Vector Index (ChromaDB)

```
~/Desktop/claude-flow/rag-pipeline/storage/chroma/
├── chroma.sqlite3           # Vector database
└── [collections]/           # Embeddings
```

**Rebuild index:**
```bash
cd ~/Desktop/claude-flow/rag-pipeline
source .venv/bin/activate
python -m ingestion.ingest
```

---

## Query Interface

### DuckDB (SQL)

```bash
# Recent events
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"

# Event types
duckdb -c "SELECT data->>'event' as event, COUNT(*)
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           GROUP BY event"

# Latency stats
duckdb -c "SELECT AVG(CAST(data->>'latency' as FLOAT))
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'gameStateUpdate'"
```

### rugs-expert (Natural Language)

```
"Show me the last 10 events"
"What fields are in playerUpdate?"
"What is the XPath for the BUY button?"
"Why is my balance not updating?"
"Explain the game phase detection logic"
```

### ChromaDB RAG

```bash
cd ~/Desktop/claude-flow/rag-pipeline
source .venv/bin/activate
python -m retrieval.retrieve "What fields are in playerUpdate?" -k 5
```

---

## Troubleshooting

### Quick Fixes

| Issue | Fix |
|-------|-----|
| CDP not responding | `pkill chrome && ./start_debugging.sh` |
| No events captured | Refresh browser (F5) after connecting |
| Missing auth events | Check wallet connected (Phantom) |
| UI frozen | `pkill -f VECTRA-PLAYER && ./run.sh` |
| Balance mismatch | Reconnect browser in UI |

**Full guide:** See `DEBUGGING_TROUBLESHOOTING.md`

---

## rugs-expert Capabilities

**Protocol Knowledge:**
- Event schema documentation
- Field definitions and types
- Auth requirements
- Phase-specific behavior

**Real-Time Queries:**
- Query EventStore for recent events
- Latency analysis
- Trade history
- Balance reconciliation

**Button Automation:**
- XPath/CSS selector strategies
- Multi-strategy fallback
- Visibility detection
- Retry logic

**Debugging Support:**
- Event sequence analysis
- State synchronization issues
- Connection troubleshooting
- Data integrity validation

---

## Commands Reference

### Start/Stop

```bash
# Start workflow
./start_debugging.sh

# Stop all
pkill chrome && pkill -f VECTRA-PLAYER
```

### Verify Setup

```bash
# CDP running?
curl -s http://localhost:9222/json/version | jq .Browser

# Events captured?
ls -lht ~/rugs_data/events_parquet/doc_type=ws_event/ | head -5
```

### Query Data

```bash
# Recent events (DuckDB)
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"

# Event count
duckdb -c "SELECT COUNT(*) FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'"
```

### Export

```bash
# Backup data
tar -czf ~/rugs_data_backup_$(date +%Y%m%d).tar.gz ~/rugs_data/

# Export to JSONL
duckdb -c "COPY (SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet')
           TO '~/rugs_data/exports/events.jsonl' (FORMAT JSON, ARRAY false)"
```

---

## Knowledge Base Files

**Canonical Protocol Spec:**
- `/home/nomad/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md`

**Browser Connection Guide:**
- `/home/nomad/Desktop/claude-flow/knowledge/rugs-events/RUGS_BROWSER_CONNECTION.md`

**Debugging Workflows:**
- `/home/nomad/Desktop/VECTRA-PLAYER/docs/DEBUGGING_QUICKSTART.md`
- `/home/nomad/Desktop/VECTRA-PLAYER/docs/WEBSOCKET_DEBUGGING_WORKFLOW.md`
- `/home/nomad/Desktop/VECTRA-PLAYER/docs/RUGS_EXPERT_CHEATSHEET.md`
- `/home/nomad/Desktop/VECTRA-PLAYER/docs/DEBUGGING_TROUBLESHOOTING.md`

---

## Next Steps

1. **First Time Users:**
   - Read `DEBUGGING_QUICKSTART.md`
   - Run `./start_debugging.sh`
   - Connect to browser in VECTRA-PLAYER UI
   - Play a few games and watch events

2. **Developers:**
   - Read `WEBSOCKET_DEBUGGING_WORKFLOW.md`
   - Review `RUGS_EXPERT_CHEATSHEET.md`
   - Practice DuckDB queries
   - Ask rugs-expert questions

3. **Protocol Researchers:**
   - Collect 100+ samples per event type
   - Analyze field patterns
   - Document findings in canonical spec
   - Update ChromaDB index

4. **Automation Engineers:**
   - Study BrowserBridge selector strategies
   - Test XPath reliability
   - Build automation scripts
   - Integrate with VECTRA-PLAYER

---

## Support

**Questions about events?**
- Ask rugs-expert in Claude Code

**Technical issues?**
- See `DEBUGGING_TROUBLESHOOTING.md`

**Feature requests?**
- File GitHub issue on VECTRA-PLAYER repo

**Protocol updates?**
- Propose changes to canonical spec
- rugs-expert will verify and update

---

**Document Status:** Production Ready
**Last Updated:** 2025-12-24
**Maintained By:** rugs-expert agent

---

## License

Same as VECTRA-PLAYER (fork of REPLAYER).
