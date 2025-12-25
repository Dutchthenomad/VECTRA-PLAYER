# WebSocket Debugging Quick Start

**Setup Time:** 2 minutes
**Purpose:** Monitor rugs.fun WebSocket events in real-time

---

## Start Monitoring (3 Commands)

```bash
# 1. Start Chrome with CDP
pkill chrome && google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  "https://rugs.fun" &

# 2. Launch VECTRA-PLAYER
./run.sh &

# 3. In VECTRA-PLAYER UI:
#    Menu → Browser → Connect to Live Browser
#    Menu → Sources → Live WebSocket Feed
```

---

## Verify Setup

```bash
# Check CDP is running
curl -s http://localhost:9222/json/version | jq .Browser

# Check events are being captured
cd ~/rugs_data/events_parquet/doc_type=ws_event && ls -lh | tail -5
```

---

## Common Queries

### Recent Events
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"
```

### Your Balance History
```bash
duckdb -c "SELECT timestamp, data->>'balance' as balance
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'playerUpdate'
           ORDER BY timestamp DESC LIMIT 10"
```

### Event Types Count
```bash
duckdb -c "SELECT data->>'event' as event, COUNT(*) as count
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           GROUP BY data->>'event'
           ORDER BY count DESC"
```

---

## Troubleshooting

### No events captured?
```bash
# Refresh page after connecting
# In browser: F5
# Wait 2 seconds for Socket.IO reconnect
```

### CDP not responding?
```bash
pkill chrome
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  "https://rugs.fun"
```

---

## Ask rugs-expert

- "What fields are in playerUpdate?"
- "Show me the last 10 events"
- "What is the XPath for the BUY button?"
- "Explain the gameStateUpdate event"

---

**Full Documentation:** `/home/nomad/Desktop/VECTRA-PLAYER/docs/WEBSOCKET_DEBUGGING_WORKFLOW.md`
