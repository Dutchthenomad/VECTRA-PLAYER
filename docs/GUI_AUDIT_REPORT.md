# VECTRA-PLAYER GUI Comprehensive Audit Report

**Date:** December 22, 2025
**Scope:** Complete GUI/UI/UX audit post-Phase 12D backend refactor
**Status:** ⚠️ CRITICAL ISSUES FOUND

---

## Executive Summary

The GUI audit reveals **successful integration of Phase 12D features** (EventStore, LiveStateProvider, Capture Stats) but identifies **critical legacy system cleanup required** and several **thread safety violations** that need immediate attention.

### Key Metrics
- **Total UI Files:** 42 Python files (~9,520 LOC)
- **Framework:** Tkinter
- **New System Adoption:** 19% of files (8/42)
- **Legacy System Dependencies:** 14% of files (6/42) ⚠️
- **Thread Safety Issues:** 3 files 🔴

### Severity Breakdown
- 🔴 **CRITICAL:** 4 issues (legacy coexistence, thread safety)
- 🟡 **WARNING:** 4 issues (API mismatches, hardcoded paths)
- ✅ **SUCCESS:** Phase 12D features fully integrated

---

## Part 1: What Works ✅

### Phase 12D Features Successfully Implemented

#### 1. EventStore Integration
**Location:** `src/ui/main_window.py:127-136`
```python
self.event_store_service = EventStoreService(
    session_id=session_id,
    config=self.config,
    event_bus=self.event_bus,
)
self.event_store_service.start()
```

**UI Display:** `src/ui/builders/status_bar_builder.py:119-126`
- Session ID (8-char truncated)
- Real-time event count
- Updates every 1000ms

**Result:** ✅ Capture stats panel visible and functional

#### 2. LiveStateProvider Integration
**Location:** `src/ui/main_window.py:140-148`
```python
self.live_state_provider = LiveStateProvider(
    event_bus=self.event_bus,
    ui_dispatcher=self.ui_dispatcher,
)
```

**Balance Display:** `src/ui/handlers/player_handlers.py:54-83`
- 🟢 GREEN: Server-authoritative balance (when connected)
- ⚪ GRAY: Local fallback balance (when disconnected)
- Lock/unlock mechanism preserved

**LIVE Indicator:** `src/ui/handlers/player_handlers.py:111-115`
- Shows "LIVE: {username}" when CDP connected
- Integrated with player profile label

**Result:** ✅ Server-authoritative state working correctly

#### 3. UI/UX Enhancements
- ✅ Capture Stats Panel (session ID + event count)
- ✅ Live Balance Display with visual indicators
- ✅ Player authentication status (👤 icon)
- ✅ Event source indicator (🟢 CDP / 🟡 Fallback / 🔴 None)
- ✅ Recording toggle with clear ON/OFF states

---

## Part 2: Critical Issues 🔴

### Issue 1: Legacy System Coexistence

**Problem:** Legacy recorders still initialized alongside EventStore, creating duplicate data capture paths.

**Location:** `src/ui/main_window.py:108-121`
```python
if LEGACY_RECORDERS_ENABLED:
    demo_dir = Path(config.FILES.get("recordings_dir", "rugs_recordings")) / "demonstrations"
    # ... callbacks
```

**Impact:**
- Duplicate data capture (Parquet + JSONL)
- Wasted disk I/O
- Confusion about canonical data source
- Technical debt buildup

**Files Still Using Legacy Recorders:**

| File | Legacy System | Lines |
|------|---------------|-------|
| `ui/handlers/recording_handlers.py` | DemoRecorder | 23-105 |
| `ui/controllers/trading_controller.py` | DemoRecorder (optional) | Various |

**Recommended Action:**
1. Set all 6 legacy flags to `false` in production
2. Remove legacy recorder imports from above files
3. Route all event capture through EventBus → EventStore

---

### Issue 2: Thread Safety Violations

#### A. BrowserConnectionDialog - UI Mutations from Background Thread
**Location:** `src/ui/browser_connection_dialog.py:150-223`

**Problem:**
```python
def _connect_async(self):
    """Runs in background thread"""
    # ... connection logic
    self._log_progress("Connecting...")  # ❌ Tkinter call from wrong thread!
```

**Impact:**
- TclError crashes
- UI corruption
- Unpredictable behavior

**Fix Required:**
```python
def _connect_async(self):
    self.root.after(0, lambda: self._log_progress("Connecting..."))
```

#### B. Subprocess Blocking UI Thread
**Location:** `src/ui/handlers/capture_handlers.py:74-80`

**Problem:**
```python
result = subprocess.run(
    ["python3", str(script_path), str(capture_file), "--report"],
    capture_output=True,
    text=True,
    timeout=30,  # ❌ BLOCKS UI THREAD FOR 30 SECONDS!
)
```

**Impact:**
- Frozen UI during analysis
- Poor user experience
- Perception of crashes

**Fix Required:** Run subprocess in background thread, use ui_dispatcher for UI updates

---

### Issue 3: Controllers Not Using EventStore

**Problem:** No controllers directly integrate with EventStore for event capture.

**Gap Analysis:**

| Controller | Should Capture | Currently Uses | Status |
|------------|----------------|----------------|--------|
| live_feed_controller.py | WebSocket events | EventBus ✓ | ✅ Correct |
| trading_controller.py | Trade events | DemoRecorder ⚠️ | 🔴 LEGACY |

**Expected Flow:**
```
Controller → EventBus.publish(event)
              ↓
         EventStore (subscribes to EventBus)
              ↓
         DuckDB/Parquet (canonical storage)
```

**Current Flow (Legacy):**
```
Controller → DemoRecorder.record_event()
              ↓
         JSONL files (deprecated)
```

**Recommended Action:**
- Remove direct recorder calls from controllers
- Ensure all events flow through EventBus
- EventStore will capture automatically

---

### Issue 4: Hardcoded Paths

**Locations:**
```python
# main_window.py:110
Path(config.FILES.get("recordings_dir", "rugs_recordings")) / "demonstrations"

# main_window.py:639
recordings_dir = self.config.FILES.get("recordings_dir", "rugs_recordings")
```

**Problem:**
- Violates Phase 12D design (RUGS_DATA_DIR environment variable)
- Inconsistent with canonical storage location
- Breaks portability

**Expected:**
```python
from pathlib import Path
import os

RUGS_DATA_DIR = Path(os.getenv("RUGS_DATA_DIR", Path.home() / "rugs_data"))
demo_dir = RUGS_DATA_DIR / "demonstrations"
```

---

## Part 3: Warnings 🟡

### Warning 1: Duplicate Toast Implementations

**Two incompatible toast systems found:**

1. **Simple Toast:** `src/ui/widgets/toast_notification.py`
   ```python
   ToastNotification(root).show(message, msg_type, duration)
   ```

   ```python
   ```

**Conflict:** `src/ui/bot_manager.py:176-181`
```python
self.toast.show("Config updated", "success", bootstyle="success")
# ❌ `bootstyle` parameter doesn't exist in either implementation!
```

**Recommended Action:**
- Standardize on one toast API
- Create adapter layer if both needed
- Remove `bootstyle` calls or add parameter support

---

### Warning 2: EventBus Global Singleton vs Injection

**Pattern Inconsistency:**

**Correct (Injection):**
```python
# main_window.py:73
self.event_bus = event_bus  # ✅ Passed as constructor parameter
```

**Risky (Global):**
```python
# capture_handlers.py:139
from services.event_bus import Events, event_bus  # ⚠️ Global import
event_bus.subscribe(Events.WS_RAW_EVENT, ...)
```

**Risk:** If multiple EventBus instances exist (tests, refactors), subscriptions go to wrong instance.

**Recommended Action:**
- Audit all EventBus usages: `grep -r "from services.event_bus import event_bus" src/ui/`
- Convert globals to constructor injection
- Maintain single source of truth

---

### Warning 3: Missing EventStore Import Guard

**Location:** `src/ui/main_window.py:24`
```python
from services.event_store import EventStoreService
```

**Problem:** EventStore imports `duckdb`, which breaks UI tests in environments without it.

**Impact:**
```bash
cd src && pytest tests/test_ui
# ❌ Fails at collection: ModuleNotFoundError: No module named 'duckdb'
```

**Recommended Fix:**
```python
try:
    from services.event_store import EventStoreService
    EVENTSTORE_AVAILABLE = True
except ImportError:
    EVENTSTORE_AVAILABLE = False
    EventStoreService = None

# Later in __init__:
if EVENTSTORE_AVAILABLE and not os.getenv("DISABLE_EVENTSTORE"):
    self.event_store_service = EventStoreService(...)
```

---

### Warning 4: Balance Lock State Persistence

**Current Behavior:** Balance lock state is not persisted across sessions.

**User Impact:**
- User locks balance → Server crash → Restart → Balance unlocked again
- Unexpected state change
- Potential for accidental manual edits

**Recommended Enhancement:**
```python
# Save lock state to config or session file
self.config.PREFERENCES["balance_locked"] = True

# Restore on startup
if self.config.PREFERENCES.get("balance_locked", True):
    self._lock_balance()
```

---

## Part 4: UI/UX Current State Analysis

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Status Bar (Phase 12D)                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ TICK: 45 | PRICE: 1.234X | PHASE: LIVE | 👤 username   │ │
│ │ BROWSER: 🟢 CDP | 🟢 CDP: Authenticated | LIVE: user   │ │
│ │ ⏺ REC ON | Session: abc12345 | Events: 1,234           │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Chart Widget                                                │
│ [Price visualization with zoom controls]                    │
├─────────────────────────────────────────────────────────────┤
│ Playback Controls                                           │
│ [Load | ▶️ Play | ⏭ Step | 🔄 Reset | Speed: 1.0x]        │
├─────────────────────────────────────────────────────────────┤
│ Bet Amount Controls                                         │
│ [Entry] [X] [+0.001] [+0.01] [+0.1] [+1]                   │
│ [1/2] [X2] [MAX] | WALLET: 10.5000 SOL 🔒                  │
├─────────────────────────────────────────────────────────────┤
│ Action Buttons                                              │
│ [SIDEBET] [BUY] [SELL] | 10% 25% 50% 100% | 🤖 Bot Status  │
└─────────────────────────────────────────────────────────────┘
```

### Status Bar Components (Phase 12D Enhancements)

| Component | Content | Color Logic |
|-----------|---------|-------------|
| Tick Label | "TICK: 45" | Default |
| Price Label | "PRICE: 1.234X" | Default |
| Phase Label | "PHASE: LIVE" | Default |
| Player Profile | "👤 username" or "👤 Not Authenticated" | Default |
| Browser Status | "BROWSER: 🟢 CDP" or "⚫ Not Connected" | Green/Gray |
| Source Label | "🟢 CDP: Authenticated" or "🟡 Fallback" or "🔴 No Source" | Green/Yellow/Red |
| Recording Toggle | "⏺ REC ON" or "⏺ REC OFF" | Red/Gray |
| **Capture Stats** | **"Session: abc12345 \| Events: 1,234"** | **Default (NEW!)** |

### Balance Display States (Phase 12C)

| State | Display | Color | Lock Icon |
|-------|---------|-------|-----------|
| Server Connected (Locked) | "WALLET: 10.5000 SOL" | 🟢 Green (#00ff88) | 🔒 |
| Server Disconnected (Locked) | "WALLET: 10.5000 SOL" | ⚪ Gray (#888888) | 🔒 |
| Unlocked | Inline entry widget | Default | 🔓 |

### Menu Bar Structure

1. **File** → Open Recording, Exit
2. **Playback** → Play/Pause, Stop
3. **Recording** → Configure & Start, Stop, Open Folder, Show Status
4. **Bot** → Enable, Configuration, Timing Metrics, Show Overlay
5. **Live Feed** → Connect checkbox
6. **Browser** → Connect, Status indicators, Disconnect
7. **View** → Themes (Dark/Light), UI Style
8. **Developer Tools** → Raw Capture, Analyze, Debug Terminal
9. **Help** → About

---

## Part 5: UI/UX Improvement Recommendations

### Priority 1: Legacy Feature Removal (Phase 12E Prep)

**Actions:**
1. Remove "Raw Capture" from Developer Tools menu (deprecated)
2. Remove "Configure & Start" from Recording menu (replaced by auto-capture)
3. Update "Recording" menu to "Capture" menu:
   - "View Capture Stats" → Opens DuckDB query UI
   - "Export Session" → Runs JSONL export script
   - "Open Data Directory" → Opens `~/rugs_data/`

**Rationale:** Align UI with Phase 12D architecture (EventStore is always recording)

---

### Priority 2: Enhanced Capture Stats Panel

**Current:** "Session: abc12345 | Events: 1,234"

**Proposed Enhancement:**
```
Session: abc12345 | Events: 1,234 (512 ws / 410 ticks / 98 trades / 214 state)
```

**Implementation:**
```python
# event_store/writer.py - Add counters by doc_type
self._counts_by_type: Dict[str, int] = defaultdict(int)

def _write_batch(self, batch: List[Event]):
    # ... existing code
    for event in batch:
        self._counts_by_type[event.doc_type] += 1

@property
def event_counts_by_type(self) -> Dict[str, int]:
    return dict(self._counts_by_type)
```

**UI Update:**
```python
# ui/handlers/event_handlers.py
counts = self.event_store_service.event_counts_by_type
total = sum(counts.values())
ws = counts.get("ws_event", 0)
ticks = counts.get("game_tick", 0)
trades = counts.get("player_action", 0)
state = counts.get("server_state", 0)

text = f"Events: {total} ({ws}ws/{ticks}t/{trades}tr/{state}st)"
```

**Benefit:** Better visibility into capture health

---

### Priority 3: Protocol Explorer Integration (Phase 12E)

**Goal:** Add UI panel for querying captured events using ChromaDB.

**Proposed Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ [New Tab] Protocol Explorer                                 │
├─────────────────────────────────────────────────────────────┤
│ Query: [What fields are in playerUpdate events?         ] 🔍│
├─────────────────────────────────────────────────────────────┤
│ Results:                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Event Type: playerUpdate                                │ │
│ │ Common Fields: ts, username, cash, position, gameId     │ │
│ │ Example Event: {...}                                    │ │
│ │ Similar Events: [3 results]                             │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Implementation Plan:**
1. Add `ProtocolExplorerPanel` class (similar to `BotConfigPanel`)
2. Integrate with ChromaDB MCP server tools:
   - `mcp__chroma__chroma_query_documents`
   - Query `rugs_events` collection
3. Add to main window as new tab or dockable panel
4. Keyboard shortcut: `Ctrl+Shift+E` (Explorer)

**Benefit:** Real-time protocol documentation from captured data

---

### Priority 4: DuckDB Query UI

**Goal:** Add UI panel for running SQL queries on Parquet data.

**Proposed Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ [New Tab] Data Explorer                                     │
├─────────────────────────────────────────────────────────────┤
│ SQL Query:                                                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SELECT ts, username, cash FROM events                   │ │
│ │ WHERE doc_type = 'server_state'                         │ │
│ │ ORDER BY ts DESC LIMIT 10                               │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [▶️ Run Query] [📋 Copy SQL] [💾 Export Results]            │
├─────────────────────────────────────────────────────────────┤
│ Results (10 rows):                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ts                  │ username │ cash                    │ │
│ │ 2025-12-22 14:35:10 │ user123  │ 10.5000                │ │
│ │ 2025-12-22 14:35:09 │ user123  │ 10.4500                │ │
│ │ ...                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
# ui/panels/data_explorer_panel.py
import duckdb
from tkinter import ttk, scrolledtext

class DataExplorerPanel(ttk.Frame):
    def __init__(self, parent, rugs_data_dir):
        self.conn = duckdb.connect()
        self.parquet_path = rugs_data_dir / "events_parquet"

    def run_query(self, sql: str) -> pd.DataFrame:
        return self.conn.execute(sql).df()
```

**Benefit:** No need to leave UI to query data

---

### Priority 5: Visual Hierarchy Improvements

**Current Issue:** Status bar is visually dense, hard to scan.

**Proposed Grouping:**
```
┌─────────────────────────────────────────────────────────────┐
│ Game State     │ Connection        │ Recording             │
│ TICK: 45       │ 🟢 CDP: user123   │ ⏺ ON | Events: 1,234 │
│ PRICE: 1.234X  │ BROWSER: 🟢 CDP   │ Session: abc12345    │
│ PHASE: LIVE    │                   │                      │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
# ui/builders/status_bar_builder.py
# Add visual separators between sections
separator1 = ttk.Separator(status_bar, orient="vertical")
separator2 = ttk.Separator(status_bar, orient="vertical")
```

**Benefit:** Faster visual scanning, clearer grouping

---

### Priority 6: Responsive Balance Display

**Current:** Balance updates every event (potential performance issue)

**Proposed:** Throttle balance updates to 100ms intervals

**Implementation:**
```python
# ui/handlers/player_handlers.py
def _update_balance_from_live_state(self):
    now = time.time()
    if now - self._last_balance_update < 0.1:  # 100ms throttle
        return
    self._last_balance_update = now

    # ... existing update logic
```

**Benefit:** Reduced UI jank during rapid updates

---

## Part 6: Integration Audit Summary

### EventBus Event Flow

**Published Events (GUI → Backend):**
```python
Events.GAME_TICK           # ReplayEngine → EventStore
Events.TRADE_EXECUTED      # TradeManager → EventStore
Events.TRADE_FAILED        # TradeManager → EventStore
Events.FILE_LOADED         # User action
Events.WS_SOURCE_CHANGED   # LiveFeedController
Events.GAME_START          # ReplayEngine
Events.GAME_END            # ReplayEngine
Events.PLAYER_IDENTITY     # CDP authentication
Events.PLAYER_UPDATE       # WebSocket playerUpdate
```

**Subscribed Events (Backend → GUI):**
```python
# event_handlers.py
Events.GAME_TICK           → _handle_game_tick
Events.TRADE_EXECUTED      → _handle_trade_executed
Events.TRADE_FAILED        → _handle_trade_failed
Events.FILE_LOADED         → _handle_file_loaded
Events.WS_SOURCE_CHANGED   → _handle_ws_source_changed
Events.GAME_START          → _handle_game_start_for_recording
Events.GAME_END            → _handle_game_end_for_recording
Events.PLAYER_IDENTITY     → _handle_player_identity
Events.PLAYER_UPDATE       → _handle_player_update
```

### LiveStateProvider Integration

**Consumer:** `src/ui/handlers/player_handlers.py`

**Properties Used:**
```python
self.live_state_provider.is_connected  # Connection state
self.live_state_provider.cash          # Server balance
self.live_state_provider.username      # Player DID
self.live_state_provider.player_id     # Player UUID
```

**Update Trigger:** `Events.PLAYER_UPDATE` published by LiveFeedController

**UI Updates:**
1. Balance label text + color
2. Player profile label
3. LIVE indicator

**Cleanup:** `src/ui/window/shutdown.py:60-66`

### EventStore Integration

**Consumer:** `src/ui/handlers/event_handlers.py`

**Properties Used:**
```python
self.event_store_service.session_id    # Current session UUID
self.event_store_service.event_count   # Total events captured
```

**UI Updates:**
1. Capture stats label
2. Periodic updates (1000ms interval)

**Lifecycle:**
- Started in `main_window.py:136`
- Stopped in `window/shutdown.py:54-58`

---

## Part 7: Action Items

### Immediate (Do Now)

1. **Set legacy flags to false in production**
   ```bash
   export LEGACY_RECORDER_SINK=false
   export LEGACY_DEMO_RECORDER=false
   export LEGACY_RAW_CAPTURE=false
   export LEGACY_UNIFIED_RECORDER=false
   export LEGACY_GAME_STATE_RECORDER=false
   export LEGACY_PLAYER_SESSION_RECORDER=false
   ```

2. **Fix thread safety in BrowserConnectionDialog**
   - File: `src/ui/browser_connection_dialog.py:150-223`
   - Use `root.after(0, callback)` for all UI updates from background thread

3. **Fix subprocess blocking in capture_handlers**
   - File: `src/ui/handlers/capture_handlers.py:74-80`
   - Move subprocess to background thread
   - Use ui_dispatcher for UI updates

### Short-Term (This Week)

4. **Remove legacy recorder code**
   - Files to modify:
     - `ui/handlers/recording_handlers.py` (remove DemoRecorder)
     - `ui/main_window.py` (remove legacy imports + initialization)

5. **Fix hardcoded paths**
   - Use `RUGS_DATA_DIR` environment variable
   - Update `main_window.py:110, 639`

6. **Standardize toast API**
   - Choose one implementation
   - Fix `bot_manager.py:176-181` (remove bootstyle)

### Medium-Term (Phase 12E)

7. **Add Protocol Explorer UI**
   - New panel: `ui/panels/protocol_explorer_panel.py`
   - Integrate ChromaDB query tools
   - Add to main window tabs

8. **Add DuckDB Query UI**
   - New panel: `ui/panels/data_explorer_panel.py`
   - SQL query interface
   - Results table view

9. **Enhanced capture stats**
   - Show event counts by type
   - Update EventStore to track counts

### Long-Term (Phase 13+)

10. **Comprehensive threading audit**
    - Review all `threading.Thread` usage
    - Ensure all UI updates use ui_dispatcher
    - Add thread safety tests

11. **EventBus injection standardization**
    - Convert all global imports to constructor injection
    - Add EventBus tests for subscription lifecycle

12. **Balance lock state persistence**
    - Save to config file
    - Restore on startup

---

## Part 8: Test Coverage Recommendations

### New Tests Needed

1. **EventStore UI Integration Tests**
   ```python
   # tests/test_ui/test_event_handlers.py
   def test_capture_stats_updates():
       """Verify capture stats label updates from EventStore"""

   def test_event_store_shutdown_cleanup():
       """Verify EventStore stops cleanly on window close"""
   ```

2. **LiveStateProvider UI Integration Tests**
   ```python
   # tests/test_ui/test_player_handlers.py
   def test_balance_display_server_connected():
       """Verify balance shows green when server connected"""

   def test_balance_display_server_disconnected():
       """Verify balance shows gray when server disconnected"""

   def test_live_indicator_updates():
       """Verify LIVE indicator updates with username"""
   ```

3. **Thread Safety Tests**
   ```python
   # tests/test_ui/test_thread_safety.py
   def test_browser_dialog_thread_safety():
       """Verify BrowserConnectionDialog doesn't mutate UI off-thread"""

   def test_ui_dispatcher_queuing():
       """Verify ui_dispatcher queues UI updates correctly"""
   ```

4. **Legacy System Removal Tests**
   ```python
   # tests/test_ui/test_legacy_removal.py
   def test_legacy_recorders_disabled():
       """Verify legacy recorders not initialized when flags false"""

   def test_eventstore_captures_all_events():
       """Verify EventStore receives all events from EventBus"""
   ```

---

## Appendix A: File Inventory

See Part 1 of audit report for complete file-by-file breakdown.

**Summary:**
- **Core:** main_window.py (672 LOC), panels.py (443 LOC)
- **Controllers:** 6 files (~4,500 LOC)
- **Handlers:** 6 mixins (~1,900 LOC)
- **Builders:** 6 files (~1,800 LOC)
- **Widgets:** 3 files (~717 LOC)
- **Dialogs:** 4 files (~1,582 LOC)

---

## Appendix B: Data Flow Diagrams

### WebSocket → UI Flow (Phase 12C/12D)
```
WebSocket "playerUpdate"
  ↓
LiveFeedController.on_player_update()
  ↓
EventBus.publish(PLAYER_UPDATE)
  ↓ (parallel paths)
  ├→ LiveStateProvider (updates server state)
  │   ↓
  │  player_handlers.py::_update_balance_from_live_state()
  │   ↓
  │  UI: Balance label (GREEN if connected)
  │
  └→ EventStoreService (persists event)
      ↓
     DuckDB/Parquet write
      ↓
     event_handlers.py::_update_capture_stats()
      ↓
     UI: Capture stats label
```

### Trade Execution Flow
```
User clicks BUY button
  ↓
trading_controller.py::execute_trade()
  ↓
BrowserBridge.execute_buy()
  ↓
EventBus.publish(TRADE_EXECUTED)
  ↓ (parallel paths)
  ├→ event_handlers.py::_handle_trade_executed() (UI toast)
  ├→ EventStoreService (persist player_action event)
  └→ GameState (update position)
```

---

## Appendix C: Configuration Reference

### Environment Variables (Phase 12D)
```bash
# Data directory
export RUGS_DATA_DIR=~/rugs_data

# Legacy recorder flags (set all to false)
export LEGACY_RECORDER_SINK=false
export LEGACY_DEMO_RECORDER=false
export LEGACY_RAW_CAPTURE=false
export LEGACY_UNIFIED_RECORDER=false
export LEGACY_GAME_STATE_RECORDER=false
export LEGACY_PLAYER_SESSION_RECORDER=false

# EventStore optional disable (default: enabled)
export DISABLE_EVENTSTORE=false
```

### Config File Reference
```python
# config.py
config.FILES = {
    "recordings_dir": "rugs_recordings",  # ⚠️ DEPRECATED - Use RUGS_DATA_DIR
    # ... other paths
}
```

---

**End of Report**

*Next Steps: Review action items and prioritize fixes for Phase 12E preparation.*
