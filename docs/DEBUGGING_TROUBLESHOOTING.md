# WebSocket Debugging Troubleshooting Guide

**Quick Reference:** Common issues and fixes for the WebSocket debugging workflow

---

## Issue 1: CDP Connection Failed

**Symptoms:**
- VECTRA-PLAYER shows "Browser connection failed"
- `curl http://localhost:9222/json/version` returns connection refused

**Cause:** Chrome not running with CDP enabled

**Fix:**
```bash
# Kill all Chrome instances
pkill chrome

# Restart with CDP
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  "https://rugs.fun"

# Verify (should return JSON)
curl -s http://localhost:9222/json/version | jq .Browser
```

**Prevention:** Always use the startup script:
```bash
./start_debugging.sh
```

---

## Issue 2: No WebSocket Events Captured

**Symptoms:**
- Browser connected successfully
- Live feed window shows no events
- EventStore has no ws_event files

**Cause:** WebSocket created before CDP interception started

**Fix:**
```bash
# Option 1: Refresh page (F5 in browser)
# Wait 2 seconds for Socket.IO reconnection
# Events should start flowing

# Option 2: Reconnect in VECTRA-PLAYER
# Menu → Browser → Disconnect
# Menu → Browser → Connect to Live Browser
# (This forces a fresh WebSocket connection)
```

**Verify capture is working:**
```bash
cd ~/rugs_data/events_parquet/doc_type=ws_event
ls -lht | head -5  # Should show recent .parquet files
```

---

## Issue 3: Missing Authentication Events

**Symptoms:**
- See `gameStateUpdate` events (unauthenticated)
- Don't see `playerUpdate`, `usernameStatus` (authenticated)

**Cause:** Wallet not connected or WebSocket not authenticated

**Fix:**

**Step 1: Verify wallet connection**
```javascript
// In browser console (F12):
localStorage.getItem('username')
// Should return: "Dutch"

// Check Phantom extension status
// Should show "Connected to rugs.fun"
```

**Step 2: Force Socket.IO reconnect**
```javascript
// In browser console:
window.location.reload()
```

**Step 3: Verify usernameStatus received**
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'usernameStatus'
           ORDER BY timestamp DESC LIMIT 1"
```

If no results, wallet is not authenticated. Reconnect Phantom extension.

---

## Issue 4: VECTRA-PLAYER UI Frozen

**Symptoms:**
- UI not responding to clicks
- Live feed stopped updating
- Window appears hung

**Cause:** Tkinter thread deadlock or Python process crashed

**Fix:**

**Step 1: Check if process is alive**
```bash
ps aux | grep python | grep VECTRA
```

**Step 2: Force quit and restart**
```bash
pkill -f VECTRA-PLAYER
cd /home/nomad/Desktop/VECTRA-PLAYER
./run.sh
```

**Step 3: Reconnect to browser**
```
Menu → Browser → Connect to Live Browser
```

**Note:** Events captured during downtime are safe in EventStore (Parquet files).

---

## Issue 5: Events Captured But Not Displayed

**Symptoms:**
- Parquet files exist in `~/rugs_data/events_parquet/`
- Live feed window shows nothing
- No errors in logs

**Cause:** Live feed window not subscribed to EventBus

**Fix:**

**Option 1: Reopen live feed window**
```
Menu → Sources → Live WebSocket Feed
```

**Option 2: Query EventStore directly**
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"
```

**Verify EventBus subscriptions:**
```python
# In VECTRA-PLAYER Python console:
from services.event_bus import event_bus, Events
print(event_bus.has_subscribers(Events.WS_RAW_EVENT))
# Should return: True
```

---

## Issue 6: Balance Mismatch (UI vs Server)

**Symptoms:**
- Server shows balance X (in `playerUpdate`)
- UI shows balance Y (different)

**Diagnosis:**

**Step 1: Check last playerUpdate**
```bash
duckdb -c "SELECT timestamp, data->'data'->>'balance' as balance
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           WHERE data->>'event' = 'playerUpdate'
           ORDER BY timestamp DESC LIMIT 1"
```

**Step 2: Check LiveStateProvider state**
```python
# In rugs-expert query:
"What is my current balance according to LiveStateProvider?"
```

**Step 3: Identify cause**
- If playerUpdate shows correct balance → UI sync issue
- If playerUpdate shows wrong balance → server issue (rare)
- If no recent playerUpdate → connection lost

**Fix:**
```
# Force state sync:
Menu → Browser → Disconnect
Menu → Browser → Connect to Live Browser
```

---

## Issue 7: High Latency / Delayed Events

**Symptoms:**
- Events appear 5+ seconds after actions
- `gameStateUpdate` latency > 1000ms

**Diagnosis:**

```bash
duckdb -c "SELECT
  AVG(CAST(data->>'latency' as FLOAT)) as avg_latency_ms,
  MAX(CAST(data->>'latency' as FLOAT)) as max_latency_ms
FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE data->>'event' = 'gameStateUpdate'"
```

**Causes:**
1. Network congestion (server overloaded)
2. CPU throttling (browser or VECTRA-PLAYER)
3. EventBus backpressure (queue overflow)

**Fix:**

**For network latency:**
- Check server status (rugs.fun uptime)
- Use wired connection instead of WiFi

**For CPU throttling:**
```bash
# Close other Chrome tabs
# Reduce VECTRA-PLAYER rate limiting
# (requires code change - not recommended)
```

**For EventBus backpressure:**
```bash
# Check EventBus queue size
# Restart VECTRA-PLAYER to clear queue
```

---

## Issue 8: Parquet Files Corrupted

**Symptoms:**
- DuckDB queries fail with "parquet file corrupted"
- Cannot read events from EventStore

**Cause:** Partial write (VECTRA-PLAYER crashed during flush)

**Fix:**

**Step 1: Identify corrupted file**
```bash
cd ~/rugs_data/events_parquet/doc_type=ws_event
for f in *.parquet; do
  duckdb -c "SELECT COUNT(*) FROM '$f'" 2>&1 | grep -q "Error" && echo "Corrupted: $f"
done
```

**Step 2: Move to quarantine**
```bash
mkdir -p ~/rugs_data/quarantine
mv [corrupted_file].parquet ~/rugs_data/quarantine/
```

**Step 3: Verify remaining files**
```bash
duckdb -c "SELECT COUNT(*) FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'"
```

**Prevention:** Use atomic writes (EventStore should handle this, but crashes can still corrupt).

---

## Issue 9: Chrome Profile Lock Error

**Symptoms:**
- Chrome fails to start with "profile in use"
- Error: "Another Chrome instance using this profile"

**Cause:** Previous Chrome instance didn't exit cleanly

**Fix:**

```bash
# Force kill all Chrome processes
pkill -9 chrome

# Remove lock files
rm -f /home/nomad/.gamebot/chrome_profiles/rugs_bot/SingletonLock
rm -f /home/nomad/.gamebot/chrome_profiles/rugs_bot/SingletonCookie

# Restart Chrome
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  "https://rugs.fun"
```

---

## Issue 10: EventStore Disk Full

**Symptoms:**
- VECTRA-PLAYER logs show "No space left on device"
- Parquet writes failing

**Diagnosis:**
```bash
df -h ~/rugs_data
du -sh ~/rugs_data/events_parquet/
```

**Fix:**

**Option 1: Clean old sessions**
```bash
# Delete events older than 7 days
find ~/rugs_data/events_parquet/ -name "*.parquet" -mtime +7 -delete

# Verify disk space recovered
df -h ~/rugs_data
```

**Option 2: Archive to external storage**
```bash
# Create archive
tar -czf ~/rugs_data_archive_$(date +%Y%m%d).tar.gz ~/rugs_data/

# Move to external drive
mv ~/rugs_data_archive_*.tar.gz /mnt/external/

# Clean local storage
rm -rf ~/rugs_data/events_parquet/*
```

**Option 3: Enable compression** (requires EventStore config change)

---

## Issue 11: rugs-expert Not Finding Events

**Symptoms:**
- Ask "Show me last 10 events"
- rugs-expert says "No events found"

**Cause:** DuckDB query path mismatch

**Diagnosis:**
```bash
# Verify Parquet files exist
ls -lh ~/rugs_data/events_parquet/doc_type=ws_event/

# Test DuckDB query manually
duckdb -c "SELECT COUNT(*) FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'"
```

**Fix:**

**If path expansion fails (~/ not expanded):**
```bash
# Use full path instead
duckdb -c "SELECT * FROM '/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet' LIMIT 10"
```

**If no files exist:**
- EventStore not initialized
- No events captured yet
- Check VECTRA-PLAYER logs: `tail -f /tmp/vectra_player.log`

---

## Diagnostic Commands

### Check System Health

```bash
# CDP status
curl -s http://localhost:9222/json/version | jq .Browser

# VECTRA-PLAYER running?
ps aux | grep VECTRA

# Recent events?
ls -lht ~/rugs_data/events_parquet/doc_type=ws_event/ | head -5

# Disk space?
df -h ~/rugs_data

# EventStore size?
du -sh ~/rugs_data/events_parquet/
```

### Check Event Capture

```bash
# Count total events
duckdb -c "SELECT COUNT(*) FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'"

# Event types
duckdb -c "SELECT data->>'event' as event, COUNT(*)
           FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           GROUP BY data->>'event'"

# Recent events
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 5"
```

### Check Logs

```bash
# VECTRA-PLAYER logs
tail -f /tmp/vectra_player.log

# Chrome debug logs
tail -f /tmp/chrome_debug.log

# System logs (for crashes)
journalctl -f | grep -i vectra
```

---

## Prevention Checklist

Before starting a debugging session:

- [ ] Kill existing Chrome instances (`pkill chrome`)
- [ ] Verify disk space (`df -h ~/rugs_data`)
- [ ] Check CDP port availability (`lsof -i :9222`)
- [ ] Use startup script (`./start_debugging.sh`)
- [ ] Wait for green "Connected" status before playing

---

## Emergency Reset

If everything is broken and you need a clean slate:

```bash
# 1. Kill all processes
pkill chrome
pkill -f VECTRA-PLAYER

# 2. Clean locks
rm -f /home/nomad/.gamebot/chrome_profiles/rugs_bot/SingletonLock

# 3. Archive old data (optional)
tar -czf ~/rugs_data_backup_$(date +%Y%m%d_%H%M%S).tar.gz ~/rugs_data/

# 4. Reset EventStore (CAUTION: deletes all events)
# rm -rf ~/rugs_data/events_parquet/*

# 5. Restart fresh
cd /home/nomad/Desktop/VECTRA-PLAYER
./start_debugging.sh
```

---

## Getting Help from rugs-expert

If you're stuck, ask rugs-expert with context:

```
"I'm seeing error X when doing Y.
Last 10 events show: [paste DuckDB output].
VECTRA-PLAYER logs show: [paste error].
What's wrong?"
```

rugs-expert will:
1. Analyze error logs
2. Query EventStore for evidence
3. Cross-reference with known issues
4. Provide specific fix steps

---

**Document Status:** Production Ready
**Last Updated:** 2025-12-24
**See Also:**
- Quick Start: `docs/DEBUGGING_QUICKSTART.md`
- Full Workflow: `docs/WEBSOCKET_DEBUGGING_WORKFLOW.md`
- Cheat Sheet: `docs/RUGS_EXPERT_CHEATSHEET.md`
