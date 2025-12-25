# Persistent Real-Time WebSocket Debugging Workflow

**Date:** December 24, 2025
**Purpose:** Set up continuous WebSocket monitoring for rugs.fun protocol observation
**Agent:** rugs-expert

---

## Overview

This workflow enables **persistent, real-time WebSocket monitoring** while you:
- Play the game in a separate browser window
- Continue conversations with Claude Code (rugs-expert)
- Observe live events in a dedicated observation window
- Document protocol findings interactively

---

## Architecture: Leverage VECTRA-PLAYER Existing Infrastructure

VECTRA-PLAYER already has all components needed:

| Component | Location | Purpose |
|-----------|----------|---------|
| CDP Bridge | src/browser/bridge.py | Connects to Chrome via CDP |
| WebSocket Interceptor | src/sources/cdp_websocket_interceptor.py | Captures WebSocket frames |
| Live Feed | src/sources/websocket_feed.py | Parses Socket.IO events |
| EventBus | src/services/event_bus.py | Pub/sub event distribution |
| EventStore | src/services/event_store/ | Persists to Parquet |
| Live UI | src/ui/main_window.py | Real-time display |

---

## Quick Start (5 Minutes)

### Step 1: Start Chrome with CDP

```bash
pkill chrome

google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  --no-first-run \
  "https://rugs.fun"
```

Verify CDP is running:
```bash
curl -s http://localhost:9222/json/version | jq
```

### Step 2: Launch VECTRA-PLAYER

```bash
cd /home/nomad/Desktop/VECTRA-PLAYER
./run.sh
```

### Step 3: Connect to Live Browser

In VECTRA-PLAYER UI:
1. Menu → Browser → Connect to Live Browser
2. Wait for status: "Connected"
3. Menu → Sources → Live WebSocket Feed

### Step 4: Start Playing

Navigate to rugs.fun in Chrome and play normally. Events appear in real-time.

---

## Debugging Workflow Examples

### A. Field Discovery

**You:** "What fields are in playerUpdate?"

**rugs-expert:**
1. Checks canonical spec
2. Queries live EventStore data
3. Provides authoritative answer with examples

### B. Real-Time Event Analysis

**You:** "I just bought 1 SOL. What events fired?"

**rugs-expert:**
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE timestamp > now() - interval '30 seconds'
           ORDER BY timestamp DESC LIMIT 10"
```

Shows sequence:
- buyOrder (your request)
- buyOrderResponse (server confirmation)
- playerUpdate (new balance)
- gameStateUpdate (updated leaderboard)

### C. Button XPath Discovery

**You:** "What is the XPath for the SELL button?"

**rugs-expert:** Shows multi-strategy selectors from bridge.py:
- CSS: 'div[class*="_buttonSection_"]:nth-child(2)'
- Text: starts-with "SELL"
- Class: contains "sell"

---

## Live Feed Display

VECTRA-PLAYER shows:

```
Live WebSocket Feed
───────────────────────────────────

📊 gameStateUpdate                 12:34:56
   gameId: game_abc123
   price: 42.5x
   tickCount: 145
   active: true

💰 playerUpdate                    12:34:57
   balance: 9.876 SOL
   position: 0.1 SOL
   entry_price: 38.2x

✅ buyOrderResponse                12:34:58
   success: true
   amount: 0.1 SOL
   price: 42.5x
```

---

## Query Captured Data

### DuckDB Queries (SQL)

```bash
# Recent gameStateUpdate events
duckdb -c "SELECT timestamp, data->>'price' as price, data->>'tickCount' as tick
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'gameStateUpdate'
           ORDER BY timestamp DESC LIMIT 10"

# Your trade history
duckdb -c "SELECT timestamp, data->>'balance' as balance
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'playerUpdate'
           ORDER BY timestamp DESC LIMIT 20"

# Latency analysis
duckdb -c "SELECT
             AVG(CAST(data->>'latency' as FLOAT)) as avg_latency_ms
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'gameStateUpdate'"
```

### Python Queries

```python
import duckdb
import json

conn = duckdb.connect()

df = conn.execute("""
    SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
    ORDER BY timestamp DESC LIMIT 10
""").df()

for idx, row in df.iterrows():
    event_data = json.loads(row['data'])
    print(f"[{row['timestamp']}] {event_data['event']}")
```

---

## Troubleshooting

### Issue: CDP Connection Failed

```bash
# Kill all Chrome processes
pkill chrome

# Restart with CDP
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  "https://rugs.fun"

# Verify
curl -s http://localhost:9222/json/list | jq '.[0].url'

# Reconnect in VECTRA-PLAYER
# Menu → Browser → Connect to Live Browser
```

### Issue: No WebSocket Events

**Fix:** Refresh page after connecting CDP

```
1. Connect to browser
2. Browser → Refresh Page (F5)
3. Wait 2 seconds
4. Events should flow
```

**Verify:**
```bash
cd ~/rugs_data/events_parquet/doc_type=ws_event
ls -lh  # Should show recent .parquet files
```

### Issue: Missing Auth Events

**Root Cause:** Requires authenticated WebSocket

**Fix:**
1. Check wallet connected (Phantom extension)
2. Verify player identity:
   ```javascript
   // In browser console (F12):
   localStorage.getItem('username')  // Should return "Dutch"
   ```
3. Force reconnect:
   ```javascript
   window.location.reload()
   ```

---

## Data Storage

```
~/rugs_data/
├── events_parquet/              # Canonical storage
│   ├── doc_type=ws_event/       # Raw WebSocket events
│   ├── doc_type=game_tick/      # Parsed tick data
│   ├── doc_type=player_action/  # Your trades
│   └── doc_type=server_state/   # Server balance updates
│
└── manifests/
    └── schema_version.json
```

### Backup

```bash
TODAY=$(date +%Y-%m-%d)
tar -czf ~/rugs_data_backup_${TODAY}.tar.gz ~/rugs_data/
```

### Export to JSONL

```bash
duckdb -c "COPY (
    SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
    ORDER BY timestamp DESC LIMIT 1000
) TO '~/rugs_data/exports/recent_events.jsonl' (FORMAT JSON, ARRAY false)"

cat ~/rugs_data/exports/recent_events.jsonl | jq -r '.data.event' | sort | uniq -c
```

---

## Use Cases

### 1. Protocol Reverse Engineering

```
1. Play game normally
2. Trigger action (e.g., place sidebet)
3. Query EventStore for events
4. Analyze field values
5. Document in canonical spec
```

### 2. Button Automation

```
1. Inspect DOM in Chrome DevTools
2. Test selectors in BrowserBridge
3. Validate with real clicks
4. Add to SelectorStrategy
```

### 3. Latency Profiling

```
1. Record gameplay session
2. Query trade sequences
3. Calculate:
   - Client → Server
   - Server → Confirmation
   - Total roundtrip
```

### 4. Schema Validation

```
1. Collect 100+ samples per event
2. Extract field combinations
3. Infer constraints
4. Update canonical spec
```

---

## Knowledge Base Integration

### RAG Query

**rugs-expert** has access to:
1. Canonical Spec (WEBSOCKET_EVENTS_SPEC.md)
2. ChromaDB Index
3. Live EventStore Data

```bash
cd ~/Desktop/claude-flow/rag-pipeline
source .venv/bin/activate
python -m retrieval.retrieve "What fields are in playerUpdate?" -k 5
```

### Documentation Update Workflow

**You:** "Found new field rugProbability"

**rugs-expert:**
1. Verifies in EventStore
2. Proposes spec update
3. Awaits approval
4. Updates spec + re-indexes ChromaDB

---

## Continuous Conversation

While monitoring runs, ask freely:

**You:** "Balance mismatch - why?"
**rugs-expert:** Queries playerUpdate, checks LiveStateProvider, diagnoses issue

**You:** "Typical BUY latency?"
**rugs-expert:** Queries buyOrder → buyOrderResponse pairs, provides stats

**You:** "Show last sidebetResponse JSON"
**rugs-expert:** Queries EventStore, formats output

---

## Conclusion

You have:
- Real-time WebSocket monitoring (VECTRA-PLAYER UI)
- Persistent event storage (Parquet + ChromaDB)
- Query interface (DuckDB + rugs-expert)
- Continuous conversation (Claude Code)
- Protocol documentation system (RAG-powered)

No new tools needed - everything is built into VECTRA-PLAYER.

Just start the system and begin observing!

---

**Document Status:** Production Ready
**Last Updated:** 2025-12-24
**Maintained By:** rugs-expert agent
