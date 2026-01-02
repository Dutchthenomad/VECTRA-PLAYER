# Trading Architecture Refactor & UI Simplification Handoff

**Date:** 2025-12-28
**Author:** Claude (Opus 4.5)
**Status:** HANDOFF DOCUMENT - Ready for Simplified UI Implementation
**Tests:** 1149 passing

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problems Encountered](#problems-encountered)
3. [Changes Made This Session](#changes-made-this-session)
4. [Current Architecture](#current-architecture)
5. [File Structure & Key Paths](#file-structure--key-paths)
6. [Planning Documentation References](#planning-documentation-references)
7. [Data Capture Status](#data-capture-status)
8. [Remaining Work](#remaining-work)
9. [Architecture Diagrams](#architecture-diagrams)
10. [Critical Context for Future Developers](#critical-context-for-future-developers)
11. [Commands Reference](#commands-reference)
12. [Update: MinimalWindow Implementation](#update-minimalwindow-implementation-later-dec-28)
13. [Complete Priority List](#complete-priority-list-current-state)

---

## Executive Summary

This session began as **Pipeline D Validation** (training data pipeline) but pivoted to addressing a fundamental architecture flaw discovered during data validation.

### What We Found

The trading system was **blocking legitimate server requests** based on broken local state validation. When a user clicked BUY:
1. The browser bridge correctly sent the request to the server ✅
2. Local validation then checked stale/broken GameState ❌
3. Toast notifications displayed false error messages ❌
4. The user saw "Buy failed: game not active" even though the trade may have succeeded on the server

### What We Fixed

Refactored `trading_controller.py` to be **server-authoritative**:
- Removed all local validation from trade execution methods
- Browser bridge is now the only action taken on button press
- Server WebSocket responses will drive UI feedback (pending implementation)

### Current State

- **1149 tests passing**
- Trading controller simplified (no local validation)
- Pipeline C fields wired (`time_in_position`, `client_timestamp`)
- **PENDING:** Simplified UI needed before further development
- **PENDING:** Server response → UI feedback loop

---

## Problems Encountered

### Problem 1: Documentation vs Implementation Gap

**Symptom:** Pipeline C was marked "COMPLETE" in documentation, but actual ButtonEvent data showed `time_in_position=0` and `client_timestamp=None`.

**Root Cause:** The fields were defined in the `ButtonEvent` schema but never wired in `trading_controller.py`.

**Fix Applied:** Added field wiring in `_emit_button_event()`:
```python
# Pipeline C: Get time_in_position from LiveStateProvider
time_in_position = 0
if self.live_state_provider and self.live_state_provider.is_live:
    time_in_position = self.live_state_provider.time_in_position

# Pipeline C: Capture client timestamp for latency tracking
client_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
```

### Problem 2: Local Validation Blocking Server Requests

**Symptom:** Toast notifications showed "game not active yet" or "BUY not allowed" even when the game was clearly active in the browser.

**Root Cause Chain:**
```
User clicks BUY
    ↓
TradingController.execute_buy()
    ↓
browser_bridge.on_buy_clicked()  ← THIS WORKS (sends to server)
    ↓
trade_manager.execute_buy()
    ↓
validate_buy() checks local GameState
    ↓
GameState.get_current_tick() returns stale data
    ↓
validate_trading_allowed() returns (False, "game not active")
    ↓
Toast shows ERROR based on LOCAL state (not server reality)
```

**Why Local State Was Wrong:**
- Local `GameState` was tied to a broken connection layer
- The connection layer wasn't properly receiving/processing WebSocket events
- Even when WebSocket data was received, event structure mismatches caused parsing failures
- Result: `GameState` thought the game wasn't active when it actually was

**Fix Applied:** Removed local validation entirely from trade execution. Browser/server is source of truth.

### Problem 3: UI Complexity Preventing Backend Completion

**User Feedback (verbatim):**
> "THE UI IS RIDDLED WITH BUGS AND IS ONLY USED FOR TESTING UNTIL WE GET TO THE POINT IN THE PLAN TO FIX THE UI BUT ITS CLEAR THAT WE DONT HAVE A LARGE ENOUGH CONTEXT WINDOW FOR YOU TO BE ABLE TO MAINTAIN THAT UNDERSTANDING EFFECTIVELY."

**Resolution:** Build simplified UI first to complete backend, then build proper UI later.

---

## Changes Made This Session

### File: `src/ui/controllers/trading_controller.py`

#### Method: `execute_buy()` (Lines 216-234)

**Before (47 lines):**
```python
def execute_buy(self):
    """Execute buy action using TradeManager."""
    self._emit_button_event("BUY")

    try:
        self.browser_bridge.on_buy_clicked()
    except Exception as e:
        logger.warning(f"Browser bridge unavailable for BUY: {e}")

    amount = self.get_bet_amount()  # ← LOCAL VALIDATION
    if amount is None:
        return  # ← BLOCKED

    result = self.trade_manager.execute_buy(amount)  # ← MORE LOCAL VALIDATION

    if result["success"]:
        self.toast.show(f"Bought {amount} SOL...", "success")
    else:
        self.toast.show(f"Buy failed: {result['reason']}", "error")  # ← FALSE ERROR
```

**After (18 lines):**
```python
def execute_buy(self):
    """
    Execute buy action - SERVER AUTHORITATIVE.

    Flow: Button press → Browser bridge → Server → WebSocket response → UI
    No local validation - server determines success/failure.
    """
    self._emit_button_event("BUY")

    try:
        self.browser_bridge.on_buy_clicked()
        self.log("BUY sent to server")
    except Exception as e:
        logger.warning(f"Browser bridge unavailable for BUY: {e}")
        self.log(f"BUY failed: No browser connection")

    # Server response via WebSocket will trigger appropriate UI feedback
```

#### Method: `execute_sell()` (Lines 236-254)

Same pattern - removed `trade_manager.execute_sell()` call and toast logic.

#### Method: `execute_sidebet()` (Lines 256-274)

Same pattern - removed `trade_manager.execute_sidebet()` call and toast logic.

### File: `src/ui/controllers/trading_controller.py` - Pipeline C Wiring

Added to `_emit_button_event()` method (Lines 170-196):
```python
# Pipeline C: Get time_in_position from LiveStateProvider
time_in_position = 0
if self.live_state_provider and self.live_state_provider.is_live:
    time_in_position = self.live_state_provider.time_in_position

# Pipeline C: Capture client timestamp for latency tracking
client_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

# Create ButtonEvent with Pipeline C fields
event = ButtonEvent(
    ...
    time_in_position=time_in_position,
    client_timestamp=client_timestamp,
)
```

---

## Current Architecture

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| CDP WebSocket Interception | ✅ Working | Captures all WebSocket traffic |
| LiveStateProvider | ✅ Working | Parses gameStateUpdate, playerUpdate |
| EventBus | ✅ Working | Pub/sub event distribution |
| EventStore (Parquet) | ✅ Working | Writing events to ~/rugs_data/ |
| ButtonEvent Emission | ✅ Working | RL training data capture |
| Browser Bridge | ✅ Working | Sends clicks to browser |

### What's Broken/Incomplete

| Component | Status | Issue |
|-----------|--------|-------|
| GameState local tracking | ❌ Broken | Doesn't reflect server reality |
| Toast notifications | ⚠️ Partial | Some based on local state (now removed from trading) |
| Trade validation | ❌ Removed | Was blocking legitimate trades |
| Server response → UI | ⏳ Pending | Need to wire WebSocket responses to toasts |

### Data Flow (Current)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER ACTION                                     │
│                         (clicks BUY button)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  TradingController.execute_buy()                                            │
│                                                                              │
│  1. _emit_button_event("BUY")                                               │
│     └── Creates ButtonEvent with full game context                          │
│     └── Publishes to EventBus (Events.BUTTON_PRESS)                         │
│     └── EventStore writes to Parquet                                        │
│                                                                              │
│  2. browser_bridge.on_buy_clicked()                                         │
│     └── Sends click command to browser via CDP                              │
│                                                                              │
│  3. self.log("BUY sent to server")                                          │
│     └── Logs to debug terminal                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Browser (Chromium via CDP)                                                 │
│                                                                              │
│  - Clicks the actual BUY button on rugs.fun                                 │
│  - Browser handles authentication, validation                                │
│  - Request sent to rugs.fun backend                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  rugs.fun Server                                                            │
│                                                                              │
│  - Validates request (balance, game state, etc.)                            │
│  - Executes trade if valid                                                  │
│  - Broadcasts WebSocket events:                                             │
│    • standard/newTrade (public - everyone sees the trade)                   │
│    • playerUpdate (private - our new balance/position)                      │
│    • success/error response (private - trade confirmation)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CDP WebSocket Interception                                                 │
│                                                                              │
│  - Captures all WebSocket frames                                            │
│  - Publishes to EventBus (Events.WS_RAW_EVENT)                              │
│  - EventStore writes raw events to Parquet                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LiveStateProvider                                                          │
│                                                                              │
│  - Parses gameStateUpdate → updates current_tick, current_price, etc.       │
│  - Parses playerUpdate → updates cash, position_qty, etc.                   │
│  - Publishes parsed events to EventBus                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  UI Feedback                                                    [PENDING]   │
│                                                                              │
│  - Toast notifications based on server response                             │
│  - Balance/position display updates                                         │
│  - Trade confirmation indicators                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure & Key Paths

### Repository Root
```
/home/nomad/Desktop/VECTRA-PLAYER/
```

### Source Code
```
src/
├── ui/
│   ├── controllers/
│   │   └── trading_controller.py    # ← MODIFIED (server-authoritative)
│   ├── handlers/
│   │   └── toast_handlers.py        # EventBus-driven toasts
│   └── main_window.py               # Main UI window
├── core/
│   ├── game_state.py                # Local state (BROKEN - don't trust)
│   ├── trade_manager.py             # Trade execution (NO LONGER CALLED FROM UI)
│   └── validators.py                # Validation functions (NO LONGER CALLED FROM UI)
├── services/
│   ├── event_bus.py                 # Pub/sub event system
│   ├── event_store/                 # Parquet writer
│   └── live_state_provider.py       # Server state from WebSocket
├── browser/
│   ├── bridge.py                    # Browser automation bridge
│   └── cdp/                         # CDP WebSocket interception
└── models/
    └── events/
        └── button_event.py          # ButtonEvent dataclass
```

### Data Storage
```
~/rugs_data/                         # RUGS_DATA_DIR
├── events_parquet/                  # Canonical event storage
│   ├── doc_type=ws_event/           # Raw WebSocket events
│   ├── doc_type=button_event/       # User button presses
│   ├── doc_type=player_action/      # (legacy)
│   └── doc_type=server_state/       # (legacy)
└── manifests/
    └── schema_version.json
```

### Documentation
```
docs/
├── reports/
│   └── TRADING-ARCHITECTURE-REFACTOR-AND-UI-SIMPLIFICATION-HANDOFF-2025-12-28.md  # THIS FILE
├── plans/
│   ├── GLOBAL-DEVELOPMENT-PLAN.md   # Master development plan
│   └── PIPELINE-D-VALIDATION-PROMPT.md  # Pipeline D validation guide
└── MIGRATION_GUIDE.md
```

### Session Context
```
.claude/
└── scratchpad.md                    # Session-level context (updated)
```

---

## Planning Documentation References

### Primary Documents

| Document | Path | Purpose |
|----------|------|---------|
| **GLOBAL-DEVELOPMENT-PLAN.md** | `docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` | Master plan - single source of truth |
| **Observation Space Design** | `scripts/FLOW-CHARTS/observation-space-design.md` | 36-feature observation space spec |
| **Pipeline D Validation** | `docs/plans/PIPELINE-D-VALIDATION-PROMPT.md` | Validation session guide |

### Reference Documents (in sandbox/DEVELOPMENT DEPRECATIONS/)

These are historical - do not follow as primary guidance:
- `2025-12-15-canonical-database-design.md`
- `2025-12-17-duckdb-query-layer-design.md`
- `2025-12-21-phase-12d-system-validation-and-legacy-consolidation.md`
- `2025-12-23-expanded-event-schema-design.md`

### External References

| Document | Path | Purpose |
|----------|------|---------|
| WebSocket Protocol Spec | `~/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` | Event structure definitions |
| Development Standard | `~/Desktop/claude-flow/docs/plans/DEVELOPMENT-DOCUMENTATION-AND-GATING-STANDARD.md` | Gating requirements |

---

## Data Capture Status

### Current Parquet Inventory

```
doc_type         count
-----------      ------
ws_event         31,744
button_event        204  (+ new captures with client_timestamp)
player_action         2
server_state          1
game_tick             1

Distinct games:      59
```

### ButtonEvent Field Status

| Field | Category | Status | Notes |
|-------|----------|--------|-------|
| `ts` | Core | ✅ Working | Timestamp |
| `button_id` | Core | ✅ Working | BUY, SELL, SIDEBET, etc. |
| `tick` | Context | ✅ Working | From LiveStateProvider |
| `price` | Context | ✅ Working | From LiveStateProvider |
| `game_id` | Context | ✅ Working | From LiveStateProvider |
| `balance` | Context | ✅ Working | From LiveStateProvider |
| `position_qty` | Context | ✅ Working | From LiveStateProvider |
| `bet_amount` | Context | ✅ Working | From UI entry field |
| `ticks_since_last_action` | Action | ✅ Working | Calculated |
| `time_in_position` | Action | ✅ Wired | From LiveStateProvider |
| `client_timestamp` | Latency | ✅ Wired | Local timestamp (ms) |
| `execution_tick` | Execution | ⏳ Pending | Requires server response matching |
| `execution_price` | Execution | ⏳ Pending | Requires server response matching |
| `trade_id` | Execution | ⏳ Pending | Requires server response matching |
| `latency_ms` | Latency | ⏳ Pending | Requires server_ts - client_ts |

---

## Remaining Work

### Immediate: Simplified UI

Build a minimal UI that:
1. Has BUY/SELL/SIDEBET buttons that call `browser_bridge` directly
2. Shows live game state from `LiveStateProvider`
3. Displays log output
4. **Does NOT** use `GameState`, `TradeManager`, or `validators.py`

### Short Term: Server Response Wiring

1. Subscribe to WebSocket events for trade confirmations
2. Parse `success`, `error`, `standard/newTrade` events
3. Display toast notifications based on server response
4. Match ButtonEvents to trade responses for execution tracking fields

### Medium Term: Pipeline D

1. Implement training data export from Parquet
2. Create observation vector builder (36 features)
3. Implement episode boundary detection
4. Create training dataset generator
5. Validate with RL environment

### Long Term: Full UI Rebuild

1. Design new UI without local state dependencies
2. Implement proper server-authoritative display
3. Remove or repurpose legacy components (`GameState`, `TradeManager`, `validators.py`)

---

## Architecture Diagrams

### Target Architecture (Server-Authoritative)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SIMPLIFIED UI                                    │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    BUY      │  │    SELL     │  │   SIDEBET   │  │  Bet Amount Entry   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘ │
│         │                │                │                                  │
│         └────────────────┼────────────────┘                                  │
│                          │                                                   │
│                          ▼                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  browser_bridge.on_*_clicked()                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                          │                                                   │
└──────────────────────────┼───────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          BROWSER (CDP)                                        │
│                                                                              │
│  - Clicks buttons in rugs.fun                                                │
│  - Handles authentication                                                    │
│  - Sends requests to server                                                  │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       RUGS.FUN SERVER                                         │
│                                                                              │
│  - Validates trades (balance, game state)                                    │
│  - Executes trades                                                           │
│  - Broadcasts WebSocket events                                               │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CDP WEBSOCKET INTERCEPTION                                 │
│                                                                              │
│  Captures:                                                                   │
│  - gameStateUpdate (tick, price, active, rugged)                             │
│  - playerUpdate (balance, position)                                          │
│  - standard/newTrade (trade broadcasts)                                      │
│  - success/error (trade confirmations)                                       │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│  EventStore  │  │   LiveState  │  │  ToastHandlers       │
│  (Parquet)   │  │   Provider   │  │  (Server Response)   │
│              │  │              │  │                      │
│  Writes all  │  │  Updates:    │  │  Shows:              │
│  events for  │  │  - tick      │  │  - Trade success     │
│  training    │  │  - price     │  │  - Trade failure     │
│  data        │  │  - balance   │  │  - Connection status │
│              │  │  - position  │  │                      │
└──────────────┘  └──────┬───────┘  └──────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         SIMPLIFIED UI DISPLAY                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Tick: 1234  │  Price: 5.67x  │  Balance: 0.123 SOL  │  Pos: 0.05 SOL  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  [Log Output Area]                                                      ││
│  │  > BUY sent to server                                                   ││
│  │  > Trade confirmed: +0.05 SOL at 5.67x                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Dependency (What to Keep vs Remove)

```
KEEP (Server-Authoritative)              REMOVE/IGNORE (Broken Local State)
─────────────────────────────            ─────────────────────────────────────
✅ browser/bridge.py                     ❌ core/game_state.py (for trading)
✅ browser/cdp/*                         ❌ core/trade_manager.py (from UI)
✅ services/live_state_provider.py       ❌ core/validators.py (from UI)
✅ services/event_store/*                ❌ UI toast based on local validation
✅ services/event_bus.py
✅ models/events/button_event.py
✅ ui/controllers/trading_controller.py (simplified)
```

---

## Critical Context for Future Developers

### DO NOT Trust Local GameState for Trading

```python
# BAD - This is broken
tick = self.state.get_current_tick()
if tick.active:  # ← UNRELIABLE
    execute_trade()

# GOOD - Let server decide
browser_bridge.on_buy_clicked()  # Server validates
# Wait for WebSocket response to confirm
```

### Toast Notifications Should Come from Server

```python
# BAD - Toast based on local validation
result = trade_manager.execute_buy(amount)
if not result["success"]:
    toast.show(result["reason"])  # ← LIE - trade may have succeeded

# GOOD - Toast based on server response
# In WebSocket event handler:
def on_trade_success(event):
    toast.show("Trade executed!", "success")

def on_trade_error(event):
    toast.show(f"Trade failed: {event['error']}", "error")
```

### LiveStateProvider IS Reliable

```python
# This is good - LiveStateProvider parses actual WebSocket data
if live_state_provider.is_live:
    current_tick = live_state_provider.current_tick
    current_price = live_state_provider.current_multiplier
    balance = live_state_provider.cash
    position = live_state_provider.position_qty
```

### The Browser Layer Works

The Puppeteer/CDP layer correctly:
- Connects to browser
- Intercepts WebSocket traffic
- Clicks buttons
- Captures events

The problem was never the browser layer - it was the local state interpretation.

---

## Commands Reference

### Run Application
```bash
cd /home/nomad/Desktop/VECTRA-PLAYER && ./run.sh
```

### Run Tests
```bash
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short
```

### Query Parquet Data
```python
import duckdb

# Count by doc_type
duckdb.query("""
    SELECT doc_type, COUNT(*)
    FROM read_parquet('/home/nomad/rugs_data/events_parquet/**/*.parquet')
    GROUP BY doc_type
""").fetchall()

# View recent ButtonEvents
duckdb.query("""
    SELECT raw_json
    FROM read_parquet('/home/nomad/rugs_data/events_parquet/doc_type=button_event/**/*.parquet')
    ORDER BY ts DESC LIMIT 5
""").fetchall()
```

### Check Git Status
```bash
cd /home/nomad/Desktop/VECTRA-PLAYER && git status
```

---

## Appendix: WebSocket Event Reference

### Events We Receive (from rugs.fun server)

| Event | Auth Required | Contains | Frequency |
|-------|---------------|----------|-----------|
| `gameStateUpdate` | No | tick, price, active, rugged, rugpool | Every tick (~4/sec) |
| `gameStatePlayerUpdate` | Yes | Our leaderboard entry | While in position |
| `playerUpdate` | Yes | cash, positionQty, avgCost | After trades |
| `standard/newTrade` | No | All trades (everyone's) | On each trade |
| `buyOrder` | Yes | Our buy confirmation | After our buy |
| `sellOrder` | Yes | Our sell confirmation | After our sell |
| `success` | Yes | Generic success | Various |
| `error` | Yes | Error message | On failures |

### Key Field Mappings

| Our Field | Server Field | Event |
|-----------|--------------|-------|
| `tick` | `tickCount` | gameStateUpdate |
| `price` | `price` | gameStateUpdate |
| `balance` | `cash` | playerUpdate |
| `position_qty` | `positionQty` | playerUpdate |
| `avg_entry_price` | `avgCost` | playerUpdate |
| `game_id` | `gameId` | gameStateUpdate |

---

---

## Update: MinimalWindow Implementation (Later Dec 28)

### What Was Built

A subsequent session implemented `MinimalWindow` (850 LOC) replacing the 8-mixin `MainWindow` (8,700 LOC):
- 93% UI code reduction
- CONNECT button for CDP connection
- Server-authoritative design
- 30 legacy UI files archived to `src/ui/_archived/`

### Blocking Issues (From Audit)

**Full audit:** `docs/MINIMAL_UI_AUDIT_REPORT.md`

| ID | Issue | Impact |
|----|-------|--------|
| **C1** | `browser_bridge` not passed to MinimalWindow | CONNECT button non-functional |
| **H2** | LiveStateProvider not created in main.py | No server-authoritative state |
| **H3** | EventStore not started | ButtonEvents NOT persisted |
| **H5** | BrowserBridge status callback not wired | Connection indicator stays red |

### Quick Fix (In main.py)

```python
# Add imports
from browser.bridge import get_browser_bridge
from services.live_state_provider import LiveStateProvider
from services.event_store.service import EventStoreService

# Before MinimalWindow creation:
self.browser_bridge = get_browser_bridge(self.event_bus)
self.live_state_provider = LiveStateProvider(self.event_bus)
self.event_store = EventStoreService(self.event_bus, self.config)
self.event_store.start()

# Pass to MinimalWindow:
self.main_window = MinimalWindow(
    self.root, self.state, self.event_bus, self.config,
    browser_bridge=self.browser_bridge,
    live_state_provider=self.live_state_provider,
)
```

### Commits Made

```
350f7d4 feat(ui): Add CONNECT button to MinimalWindow
52972c8 refactor(ui): Archive 30 deprecated UI files
26a1a2b feat(main): Replace MainWindow with MinimalWindow
3d6488a feat(ui): Wire WebSocket event handlers
22644e8 feat: Wire TradingController to MinimalWindow
6aecc4f feat(ui): Add MinimalWindow for RL training
91edbe6 docs: Add minimal UI design
```

### Current Test Count

**1138 tests passing** (after MinimalWindow implementation)

---

## Complete Priority List (Current State)

### Priority 1: Fix MinimalWindow Wiring (4 issues)
1. Pass `browser_bridge` to MinimalWindow (C1)
2. Create LiveStateProvider in main.py (H2)
3. Create and start EventStore in main.py (H3)
4. Wire BrowserBridge status callback (H5)

### Priority 2: Verify Basic Functionality
1. CONNECT button initiates CDP connection
2. Connection indicator turns green
3. Status bar updates from WebSocket
4. ButtonEvents persisted to Parquet

### Priority 3: Pipeline D
1. Training data export from Parquet
2. Observation vector builder
3. Episode boundary detection

---

*Document generated: 2025-12-28*
*Repository: /home/nomad/Desktop/VECTRA-PLAYER*
*Tests: 1138 passing (post-MinimalWindow)*
*Status: MinimalWindow wiring fixes needed before Pipeline D*
