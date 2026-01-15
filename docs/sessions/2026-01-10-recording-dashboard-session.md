# Recording Dashboard Session - 2026-01-10

**Status:** INCOMPLETE - Needs further debugging
**Priority:** Return to later

---

## What Was Built

A separate Flask-based Recording Dashboard UI at `src/recording_ui/` that:
- Opens as a tab in the same Chrome browser as rugs.fun (via CDP)
- Shows recording status and game metrics
- Displays recorded games table with price charts

### Files Created/Modified

```
src/recording_ui/
├── __init__.py
├── __main__.py
├── app.py                      # Flask app with REST API
├── services/
│   ├── __init__.py
│   ├── chrome_tab.py           # CDP tab opener (works)
│   ├── control_service.py      # Recording toggle via control file
│   ├── data_service.py         # DuckDB queries for Parquet
│   └── session_tracker.py      # Session-specific metrics (NEW)
├── static/
│   ├── css/dashboard.css
│   └── js/dashboard.js
└── templates/
    ├── base.html
    └── dashboard.html

scripts/record.sh               # One-command startup
```

### Startup Command
```bash
cd /home/devops/Desktop/VECTRA-PLAYER && ./scripts/record.sh
```

---

## The Problem

The dashboard shows **stale/placeholder stats** (888 games, 925.4K events) that don't update when recording is active and games complete.

### Root Cause (Suspected)

The dashboard queries **Parquet files** for stats, but:
1. The main UI (EventStoreService) writes to Parquet asynchronously with buffering
2. File modification times may not update until buffer flushes
3. Session tracking uses file mtime which may not reflect real-time writes

### What User Expected

- Dashboard shows games recorded THIS session only (not historical totals)
- Unique gameId count (deduplicated from rolling window)
- Updates in real-time as games complete

---

## Key Knowledge from rugs-expert

### gameHistory Mechanics
```
- Rolling 10-game window (same game appears ~10 times in consecutive captures)
- Dual-broadcast on rug:
  1. First: serverSeed revealed for ended game
  2. Second: New gameId + serverSeedHash for next game
- Must deduplicate by gameId for accurate counting
- Recording optimization: Only need to capture on rug events
```

### Data Flow
```
WebSocket → CDPWebSocketInterceptor → EventBus → EventStoreService → Parquet
                                                                        ↓
                                              Recording Dashboard ← DuckDB queries
```

---

## What Was Attempted

1. **SessionTracker service** - Tracks session start time, queries only files modified since start
2. **Session vs Total stats** - API returns both session-specific and historical totals
3. **Deduplication by gameId** - SessionTracker deduplicates when querying

### API Response (Working)
```json
{
  "session_game_count": 0,      // Games this session
  "session_event_count": 0,     // Events this session
  "total_game_count": 888,      // Historical total
  "storage_mb": 603.71
}
```

---

## What Needs Investigation

1. **Real-time data flow** - Is EventStoreService actually writing Parquet files when recording?
2. **File flush timing** - When do Parquet files get their mtime updated?
3. **Alternative approach** - Maybe dashboard should subscribe to EventBus directly instead of polling Parquet?
4. **Control file IPC** - The toggle writes to `.recording_control.json` but EventStoreService doesn't watch it

---

## Potential Solutions

### Option A: EventBus Integration
Have the dashboard connect to EventBus (like other subscribers) to receive real-time events instead of polling Parquet.

### Option B: Shared State File
EventStoreService writes a state file with current session stats that dashboard reads.

### Option C: WebSocket from Main UI
Main UI exposes a local WebSocket that dashboard connects to for live stats.

### Option D: Fix Parquet Polling
Debug why Parquet file mtime-based detection isn't working.

---

## Test Checklist (For Next Session)

- [ ] Verify EventStoreService is writing to Parquet when recording enabled
- [ ] Check Parquet file mtimes before/after game completes
- [ ] Test if `session_tracker.get_session_stats()` returns >0 after games complete
- [ ] Consider adding debug logging to trace the data flow

---

## Related Documentation

- `docs/plans/eager-napping-quokka.md` - Original plan for Flask dashboard
- `docs/rag/knowledge/rl-design/` - RL design docs
- rugs-expert MCP server - Canonical gameHistory knowledge

---

*Session saved for later continuation*
