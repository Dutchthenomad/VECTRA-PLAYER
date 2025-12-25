# WebSocket Debugging Guide

**Single source of truth for VECTRA-PLAYER debugging workflows.**

---

## Quick Start (2 Minutes)

```bash
# 1. Start Chrome + VECTRA-PLAYER
cd /home/nomad/Desktop/VECTRA-PLAYER
./start_debugging.sh

# 2. In VECTRA-PLAYER UI:
#    Menu -> Browser -> Connect to Live Browser
#    Menu -> Sources -> Live WebSocket Feed

# 3. Play game in Chrome, events appear in real-time

# 4. Query data
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"
```

---

## Architecture

```
Browser (rugs.fun)  --->  VECTRA-PLAYER  --->  EventStore (Parquet)
       CDP:9222           Live Feed UI          DuckDB queryable
                               |
                               v
                         rugs-expert
                        (Claude Code)
```

**Components:**
| Component | Purpose |
|-----------|---------|
| Chrome CDP | Browser connection on port 9222 |
| BrowserBridge | CDP WebSocket interception |
| EventStore | Parquet persistence (~rugs_data/) |
| LiveStateProvider | Server-authoritative state |
| rugs-expert | Protocol knowledge specialist |

---

## Commands Reference

### Start/Stop
```bash
./start_debugging.sh                    # Start everything
pkill chrome && pkill -f VECTRA         # Stop everything
```

### Verify Setup
```bash
curl -s http://localhost:9222/json/version | jq .Browser  # CDP OK?
ls -lht ~/rugs_data/events_parquet/doc_type=ws_event/     # Events captured?
```

### Query Data (DuckDB)
```bash
# Recent events
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"

# Event types distribution
duckdb -c "SELECT data->>'event' as event, COUNT(*)
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           GROUP BY event ORDER BY count DESC"

# Balance history
duckdb -c "SELECT timestamp, data->'data'->>'cash' as balance
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'playerUpdate'
           ORDER BY timestamp DESC LIMIT 10"

# Latency stats
duckdb -c "SELECT AVG(CAST(data->>'latency' as FLOAT)) as avg_ms
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'gameStateUpdate'"
```

### Backup/Export
```bash
tar -czf ~/rugs_data_backup_$(date +%Y%m%d).tar.gz ~/rugs_data/

duckdb -c "COPY (SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet')
           TO '~/rugs_data/exports/events.jsonl' (FORMAT JSON, ARRAY false)"
```

---

## rugs-expert Queries

Ask in Claude Code:
```
"What fields are in playerUpdate?"
"Show me the last 10 events"
"What is the XPath for the SELL button?"
"Why is my balance not updating?"
"What events fire when I BUY?"
```

---

## Troubleshooting

### CDP Connection Failed
```bash
pkill chrome
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  "https://rugs.fun"
curl -s http://localhost:9222/json/version | jq .Browser
```

### No Events Captured
1. Refresh browser page (F5) after connecting
2. Wait 2 seconds for Socket.IO reconnect
3. Check: `ls -lht ~/rugs_data/events_parquet/doc_type=ws_event/`

### Missing Auth Events (no playerUpdate)
1. Check wallet connected (Phantom extension)
2. Verify: `localStorage.getItem('username')` in browser console
3. Force reconnect: `window.location.reload()`

### UI Frozen
```bash
pkill -f VECTRA-PLAYER
./run.sh
# Then: Menu -> Browser -> Connect to Live Browser
```

### Balance Mismatch (UI vs Server)
```bash
# Check server balance
duckdb -c "SELECT timestamp, data->'data'->>'cash' as balance
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'playerUpdate'
           ORDER BY timestamp DESC LIMIT 1"
# Fix: Disconnect and reconnect browser in VECTRA-PLAYER
```

### Chrome Profile Lock
```bash
pkill -9 chrome
rm -f /home/nomad/.gamebot/chrome_profiles/rugs_bot/SingletonLock
./start_debugging.sh
```

### EventStore Disk Full
```bash
df -h ~/rugs_data
find ~/rugs_data/events_parquet/ -name "*.parquet" -mtime +7 -delete
```

---

## Data Storage

```
~/rugs_data/
├── events_parquet/
│   ├── doc_type=ws_event/       # Raw WebSocket events
│   ├── doc_type=game_tick/      # Parsed tick data
│   ├── doc_type=player_action/  # Your trades
│   └── doc_type=server_state/   # Server balance updates
└── manifests/
    └── schema_version.json
```

---

## Knowledge Base

| Resource | Location |
|----------|----------|
| Protocol Spec | `~/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` |
| ChromaDB Index | `~/Desktop/claude-flow/rag-pipeline/storage/chroma/` |
| Strategy Docs | `~/Desktop/claude-flow/knowledge/rugs-strategy/` |

**Rebuild ChromaDB index:**
```bash
cd ~/Desktop/claude-flow/rag-pipeline
source .venv/bin/activate
python -m ingestion.ingest
```

---

## Emergency Reset

```bash
pkill chrome && pkill -f VECTRA-PLAYER
rm -f /home/nomad/.gamebot/chrome_profiles/rugs_bot/SingletonLock
cd /home/nomad/Desktop/VECTRA-PLAYER
./start_debugging.sh
```

---

*Last Updated: 2025-12-24*
