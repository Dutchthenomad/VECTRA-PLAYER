# VECTRA-PLAYER Session Scratchpad

Last Updated: 2026-01-13 22:00 UTC

---

## CURRENT STATUS: Unified Control Panel COMPLETE

**Unified Dashboard:** Flask web dashboard with integrated trading controls
**One-Command Startup:** `./scripts/start.sh` launches Chrome + Dashboard
**All Tabs Verified:** Recording, Explorer, Backtest with live WebSocket feed

---

## What Was Accomplished (Jan 13, 2026 - Unified Control Panel Session)

### Session: Merge Tkinter MinimalWindow into Flask Dashboard

**Goal:** Create unified web control panel that replaces the separate Tkinter UI

**Problem Solved:**
- Previously required running TWO separate applications (Tkinter + Flask Dashboard)
- Flask dashboard couldn't connect to Chrome or execute trades
- Recording didn't work because EventBus wasn't started

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                  UNIFIED FLASK DASHBOARD                     │
├─────────────────────────────────────────────────────────────┤
│  start.sh                                                    │
│     ├── Launch Chrome with rugs_bot profile (CDP port 9222) │
│     └── Start Flask dashboard (port 5000)                   │
│                                                              │
│  Flask App (app.py)                                          │
│     ├── event_bus.start()          ← CRITICAL FIX           │
│     ├── EventStoreService          ← Parquet persistence    │
│     ├── BrowserService             ← Chrome/CDP integration │
│     └── Trading API endpoints      ← /api/trade/*           │
│                                                              │
│  Backtest Tab (backtest.html)                               │
│     ├── BUY / SIDE / SELL buttons                           │
│     ├── Bet amount controls                                  │
│     ├── Live WebSocket feed                                  │
│     └── Browser connection status                            │
└─────────────────────────────────────────────────────────────┘
```

### Files Created/Modified

**1. `src/recording_ui/services/browser_service.py` (NEW - ~400 lines)**
   - Flask-compatible wrapper for BrowserBridge
   - Synchronous API methods for Flask endpoints
   - EventBus → SocketIO forwarding for real-time updates
   - GameState tracking for UI display

**2. `src/recording_ui/app.py` (MODIFIED)**
   - Added imports: `event_bus`, `EventStoreService`
   - Added `event_bus.start()` - **CRITICAL FIX** (events weren't being delivered)
   - Added `EventStoreService` initialization and startup
   - Added browser control endpoints: `/api/browser/connect`, `/api/browser/disconnect`, `/api/browser/status`
   - Added trading endpoints: `/api/trade/buy`, `/api/trade/sell`, `/api/trade/sidebet`
   - Added bet control endpoints: `/api/trade/increment`, `/api/trade/percentage`, `/api/trade/clear`, `/api/trade/half`, `/api/trade/double`, `/api/trade/max`
   - Updated `/api/status` to use EventStoreService directly
   - Updated `/api/recording/toggle` to use EventStoreService.toggle_recording()

**3. `src/recording_ui/templates/backtest.html` (MODIFIED)**
   - Added Browser Control card in sidebar
   - Added Trading card with compact BUY/SIDE/SELL buttons
   - Added bet amount display and increment buttons
   - Added percentage buttons (25%, 50%, 100%)

**4. `src/recording_ui/static/js/backtest.js` (MODIFIED)**
   - Added trading control functions: `clickBuy()`, `clickSell()`, `clickSidebet()`
   - Added `toggleConnection()` for browser connect/disconnect
   - Added `clickIncrement()` for bet amount adjustment
   - Added `updateBrowserUI()` and `updateGameStateUI()` for real-time updates

**5. `scripts/start.sh` (MODIFIED)**
   - Fixed Chrome profile path to match CDPBrowserManager
   - Uses `--user-data-dir="$HOME/.gamebot/chrome_profiles/rugs_bot"`
   - Single command launches Chrome + Dashboard

---

## Critical Bug Fixed

### EventBus Processing Thread Not Started

**Symptom:** Recording toggle worked but no events were captured

**Root Cause:** Flask app initialized EventStoreService but never called `event_bus.start()` to start the processing thread

**Fix Applied to `app.py`:**
```python
# Start the event bus processing thread (required for event delivery)
event_bus.start()
logger.info("EventBus processing thread started")

# Initialize EventStoreService for Parquet persistence
event_store_service = EventStoreService(event_bus)
event_store_service.start()
```

**Result:** Recording now captures events correctly (verified: 2198 events, 13 games in testing)

---

## Verification Results

### Recording Tab ✅
- Recording toggle works
- Events captured: 2198
- Games captured: 13
- Training data: 10+ games, 200+ sidebets, 1400+ ticks
- EventStoreService persists to Parquet

### Explorer Tab ✅
- Page loads correctly
- API returns data: 943 total games, 362 playable
- Strategy stats and price curves available

### Backtest Tab ✅
- Trading buttons execute via Chrome CDP:
  - BUY → POST /api/trade/buy 200 ✅
  - SIDEBET → POST /api/trade/sidebet 200 ✅
  - SELL → POST /api/trade/sell 200 ✅
- Bet amount controls work (+.01 incremented bet)
- Live WebSocket feed receives real-time game data
- SocketIO connection established

---

## Commands

```bash
# Start unified control panel (one command)
./scripts/start.sh

# Or start without auto-opening browser
./scripts/start.sh --no-browser

# Dashboard URL
http://localhost:5000

# Dashboard tabs:
# - Recording: Toggle recording, view captured games
# - Explorer: Strategy analysis, Monte Carlo
# - Backtest: Live trading with WebSocket feed
# - Profiles: Trading profile management
```

---

## API Reference (New Endpoints)

### Browser Control
```
POST /api/browser/connect     # Connect to Chrome via CDP
POST /api/browser/disconnect  # Disconnect (keep Chrome running)
GET  /api/browser/status      # Connection status + game state
```

### Trading Actions
```
POST /api/trade/buy           # Click BUY button
POST /api/trade/sell          # Click SELL button
POST /api/trade/sidebet       # Click SIDEBET button
POST /api/trade/increment     # {"amount": 0.01} - add to bet
POST /api/trade/percentage    # {"pct": 50} - set sell percentage
POST /api/trade/clear         # Clear bet to 0
POST /api/trade/half          # Halve current bet
POST /api/trade/double        # Double current bet
POST /api/trade/max           # Set to max balance
```

---

## Previous Session (Monte Carlo)

Monte Carlo strategy comparison remains intact:
- `src/recording_ui/services/monte_carlo.py` - Simulation engine
- `src/recording_ui/services/monte_carlo_service.py` - 8 strategies
- `/api/explorer/monte-carlo` endpoint
- Game Explorer "Monte Carlo" tab

---

## Related Files

| Component | Location |
|-----------|----------|
| Browser Bridge | `src/browser/bridge.py` |
| CDP Manager | `src/browser/manager.py` |
| EventBus | `src/services/event_bus.py` |
| EventStoreService | `src/services/event_store/service.py` |
| Start Script | `scripts/start.sh` |

---

*Scratchpad updated - Unified Control Panel complete, all tabs verified*
