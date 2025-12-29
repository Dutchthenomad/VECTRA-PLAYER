# MinimalWindow UI Implementation Analysis Report

**Date:** December 28, 2025
**Scope:** Minimal UI implementation for RL training data collection
**Files Analyzed:** 8 core files

---

## EXECUTIVE SUMMARY

Found **17 issues** across 4 severity levels:
- **1 Critical** (prevents core functionality)
- **6 High** (missing requirements, broken wiring)
- **7 Medium** (suboptimal patterns, incomplete implementation)
- **3 Low** (minor improvements)

**Status:** System is NOT ready for production. Critical browser_bridge wiring is missing, preventing CDP connection.

---

## CRITICAL ISSUES

### C1: Browser Bridge Not Passed to MinimalWindow
**Severity:** CRITICAL
**File:** `src/main.py:226-231`
**Impact:** CONNECT button completely non-functional

**Problem:**
```python
# Line 226 - MinimalWindow creation
self.main_window = MinimalWindow(
    self.root,
    self.state,
    self.event_bus,
    self.config,
)
```

Missing parameters: `trading_controller`, `browser_bridge`, `live_state_provider`

**Fix:**
```python
# In main.py, before creating MinimalWindow
from browser.bridge import get_browser_bridge
from services.live_state_provider import LiveStateProvider

browser_bridge = get_browser_bridge()
live_state = LiveStateProvider(event_bus)

self.main_window = MinimalWindow(
    self.root,
    self.state,
    self.event_bus,
    self.config,
    browser_bridge=browser_bridge,
    live_state_provider=live_state,
)
```

---

## HIGH SEVERITY ISSUES

### H1: TradingController Dependencies Not Created
**Severity:** HIGH
**File:** `src/ui/minimal_window.py:408-446`
**Impact:** ButtonEvent emission will fail

**Problem:**
TradingController creation in MinimalWindow uses fallback MinimalDispatcher and MinimalToast, but these are incomplete stubs that just log messages instead of proper error handling.

**Issues:**
1. MinimalDispatcher has no thread safety (no `root.after()`)
2. MinimalToast doesn't display anything to user
3. Both are defined locally instead of proper implementations

**Fix:**
Create proper minimal implementations or import from existing code.

---

### H2: LiveStateProvider Not Instantiated
**Severity:** HIGH
**File:** `src/main.py`
**Impact:** Server-authoritative state unavailable, ButtonEvents missing live context

**Problem:**
LiveStateProvider is never created in main.py, so MinimalWindow and TradingController cannot access server-authoritative state (balance, position, tick, etc.).

**Fix:**
```python
# In main.py Application.__init__, after event_bus.start()
from services.live_state_provider import LiveStateProvider

self.live_state_provider = LiveStateProvider(event_bus)
```

---

### H3: EventStore Not Started
**Severity:** HIGH
**File:** `src/main.py`
**Impact:** ButtonEvents will NOT be persisted to Parquet

**Problem:**
EventStore (the single writer for Parquet persistence) is never instantiated or started in main.py. ButtonEvents published to EventBus will have no subscriber to persist them.

**Fix:**
```python
# In main.py Application.__init__
from services.event_store.service import EventStore

self.event_store = EventStore(event_bus, config)
self.event_store.start()
```

---

### H4: WebSocket Event Subscriptions Use Wrong Field Names
**Severity:** HIGH
**File:** `src/ui/minimal_window.py:537-593`
**Impact:** Status bar will not update (TICK, PRICE, PHASE, USER will stay at defaults)

**Problem:**
MinimalWindow subscribes to `WS_RAW_EVENT` and expects rugs.fun field names, but doesn't handle the EventBus wrapping correctly. Need to verify what BrowserBridge actually publishes.

---

### H5: Missing Browser Connection Status Event Subscriptions
**Severity:** HIGH
**File:** `src/ui/minimal_window.py:452-471`
**Impact:** CONNECTION indicator won't turn green when connected

**Problem:**
MinimalWindow subscribes to `WS_CONNECTED` and `WS_DISCONNECTED`, but BrowserBridge publishes `BridgeStatus` changes via callback, NOT EventBus.

**Fix:**
```python
# In MinimalWindow.__init__, after browser_bridge is set:
if self.browser_bridge:
    self.browser_bridge.on_status_change = self._on_browser_status_changed

def _on_browser_status_changed(self, status: BridgeStatus):
    from browser.bridge import BridgeStatus
    connected = (status == BridgeStatus.CONNECTED)
    self.root.after(0, lambda: self.update_connection(connected))
```

---

### H6: Percentage Button Wiring Missing
**Severity:** HIGH
**File:** `src/ui/minimal_window.py:662-670`
**Impact:** Percentage buttons don't call TradingController properly

**Problem:**
Percentage clicks should still emit ButtonEvents even without browser connection. Move ButtonEvent emission BEFORE browser click attempt.

---

## MEDIUM SEVERITY ISSUES

### M1: Missing EventBus WS_CONNECTED/WS_DISCONNECTED Publishers
**Severity:** MEDIUM
**File:** `src/browser/bridge.py`
**Impact:** MinimalWindow WS event subscriptions never fire

### M2: Phase Detection Logic Not Aligned with rugs.fun Fields
**Severity:** MEDIUM
**File:** `src/ui/minimal_window.py:485-515`
**Impact:** PHASE display may show incorrect values

### M3: Bet Entry Widget Not Validated on Button Press
**Severity:** MEDIUM
**File:** `src/ui/minimal_window.py:746-768`
**Impact:** Invalid bet amounts can be submitted

### M4: GameState Not Updated from WebSocket Events
**Severity:** MEDIUM
**File:** `src/ui/minimal_window.py`
**Impact:** Local state gets stale, fallback queries to GameState return old values

### M5: Missing Error Handling in _create_trading_controller
**Severity:** MEDIUM
**File:** `src/ui/minimal_window.py:408-446`
**Impact:** TradingController creation failure crashes UI initialization

### M6: CONNECT Button Doesn't Disable During Connection
**Severity:** MEDIUM
**File:** `src/ui/minimal_window.py:646-656`
**Impact:** User can spam CONNECT button

### M7: Balance Display Uses Wrong Precision
**Severity:** MEDIUM
**File:** `src/ui/minimal_window.py:816-819`
**Impact:** Balance shows 3 decimals, may need 4

---

## LOW SEVERITY ISSUES

### L1: Type Hints Incomplete for bet_entry
### L2: Hardcoded Colors Instead of Theme (intentional for minimal UI)
### L3: Missing Docstrings for Update Methods

---

## DATA FLOW VERIFICATION

### Button Press → ButtonEvent → Persistence

**ACTUAL Flow (with current bugs):**
1. ✅ User clicks BUY button
2. ✅ MinimalWindow calls `_on_buy_clicked()`
3. ❌ **TradingController may be broken** (MinimalDispatcher has no thread safety)
4. ❌ LiveStateProvider is None → uses stale GameState
5. ❌ EventStore is None → NOT PERSISTED
6. ❌ BrowserBridge is None → no browser click

**Result:** 0% functional

### WebSocket Event → UI Update

**ACTUAL Flow (with current bugs):**
1. ✅ BrowserBridge exists (singleton via `get_browser_bridge()`)
2. ❌ **Never connected** (no browser_bridge passed to MinimalWindow)
3. ❌ CONNECT button doesn't work → no CDP connection
4. ❌ No WebSocket events received
5. ❌ UI never updates

**Result:** 0% functional

---

## RECOMMENDATIONS

### Immediate Actions (Required for Basic Functionality)
1. **Fix C1:** Pass browser_bridge to MinimalWindow (5 min)
2. **Fix H2:** Create LiveStateProvider in main.py (5 min)
3. **Fix H3:** Create and start EventStore in main.py (10 min)
4. **Fix H5:** Wire BrowserBridge status callback (10 min)

**Estimated Time:** 30 minutes to achieve basic functionality

### Phase 2 Actions (Full Requirements)
5. **Fix H1:** Use proper TkDispatcher instead of MinimalDispatcher (15 min)
6. **Fix H4:** Verify WebSocket field names match spec (30 min)
7. **Fix H6:** Improve percentage button wiring (10 min)
8. **Fix M1:** Add EventBus publishers for connection events (10 min)

**Estimated Time:** 1 hour for complete implementation

---

## CRITICAL PATH

```
main.py creates components → MinimalWindow receives them → TradingController emits events → EventStore persists
```

**Blocking Issues:** C1, H2, H3, H5
**Must fix these 4 before ANY functionality works.**

---

*Report generated by rugs-expert agent*
