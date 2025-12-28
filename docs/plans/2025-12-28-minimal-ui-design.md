# Minimal UI Design for RL Training Data Collection

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strip VECTRA-PLAYER UI down to essential components for RL training data collection while preserving button press latency tracking.

**Architecture:** Single-file MinimalWindow replaces 8-mixin MainWindow. All visual components (charts, overlays, animations) removed. Plain text labels for status. Buttons emit ButtonEvents with timestamps, CDPWebSocketInterceptor captures server ACKs for latency calculation.

**Tech Stack:** Tkinter (plain widgets), EventBus (pub/sub), Parquet (persistence)

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              STATUS BAR                                   │
│                                                                          │
│   TICK: 0000    PRICE: 0000.00    PHASE: ACTIVE    CONNECTION: ●        │
│   USER: PLAYER123                 BALANCE: 00.000 SOL                    │
├──────────────────────────────────────────────────────────────────────────┤
│                              CONTROLS                                     │
│                                                                          │
│  ┌──────┐   [+0.001] [+0.01] [+0.1] [+1]           [1/2]  [X2]  [MAX]   │
│  │ 10%  │                                                                │
│  │ 25%  │   BET AMOUNT                                                   │
│  │ 50%  │   [X] ┌──────────────┐    [BUY]    [SIDEBET]    [SELL]        │
│  │ 100% │       │ 00.000 SOL   │    green     yellow       blue         │
│  └──────┘       └──────────────┘                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

**Components:**
- Status bar: TICK, PRICE, PHASE (text), USER, BALANCE, CONNECTION (dot)
- Percentage selector: Vertical stack (10%, 25%, 50%, 100%)
- Increment buttons: +0.001, +0.01, +0.1, +1
- Utility buttons: 1/2, X2, MAX
- Bet entry: X (clear) + input field + "SOL" label
- Action buttons: BUY (green), SIDEBET (yellow), SELL (blue)

---

## Data Sources (WebSocket Events)

| UI Element | Event | Field Path | Update Frequency |
|------------|-------|------------|------------------|
| TICK | `gameStateUpdate` | `.tickCount` | ~4x/sec |
| PRICE | `gameStateUpdate` | `.price` | ~4x/sec |
| PHASE | `gameStateUpdate` | Derived from `.active`, `.rugged`, `.cooldownTimer`, `.allowPreRoundBuys` | ~4x/sec |
| USER | `usernameStatus` | `.username` | Once on connect |
| BALANCE | `playerUpdate` | `.cash` | After each trade |
| CONNECTION | `BridgeStatus` | Internal state | On change |

**Phase Detection Logic:**
```python
def detect_phase(event: dict) -> str:
    if event.get('cooldownTimer', 0) > 0:
        return 'COOLDOWN'
    if event.get('rugged', False) and not event.get('active', False):
        return 'COOLDOWN'
    if event.get('allowPreRoundBuys', False) and not event.get('active', False):
        return 'PRESALE'
    if event.get('active', False) and not event.get('rugged', False):
        return 'ACTIVE'
    if event.get('rugged', False):
        return 'RUGGED'
    return 'UNKNOWN'
```

---

## Latency Tracking Flow

```
UI Button Press
     │
     ├─→ Record client_ts (ms)
     ├─→ ButtonEvent emitted to EventBus
     └─→ BrowserBridge clicks browser button
              │
              ↓
         Browser sends: 42XXXX["buyOrder", {...}]
              │
              ↓
         Server responds: 43XXXX[{success: true, timestamp: ...}]
              │
              ↓
         CDPWebSocketInterceptor captures response
              │
              ↓
         Match & calculate latency
```

**Server ACK Events:**

| Action | Request | Response | Timestamp Field |
|--------|---------|----------|-----------------|
| BUY | `buyOrder` | `43XXXX[{success, timestamp}]` | `timestamp` |
| SELL | `sellOrder` | `43XXXX[{success, timestamp}]` | `timestamp` |
| SIDEBET | `requestSidebet` | `43XXXX[{success, sidebet}]` | `sidebet.timestamp` |

**Latency Calculation:**
```python
client_ts    = button_press_time_ms      # When UI button clicked
server_ts    = response['timestamp']      # Server's timestamp in ACK
confirmed_ts = time_received_ms           # When we see the 43XXXX

send_latency    = server_ts - client_ts   # Client → Server
confirm_latency = confirmed_ts - server_ts # Server → Client
total_latency   = confirmed_ts - client_ts # Round-trip
```

---

## Components to KEEP

| Component | File | LOC | Reason |
|-----------|------|-----|--------|
| TradingController | `controllers/trading_controller.py` | 484 | ButtonEvent emission + latency |
| BrowserBridge | `browser/bridge.py` | 951 | CDP connection + button clicks |
| CDPWebSocketInterceptor | `sources/cdp_websocket_interceptor.py` | ~400 | Captures server events |
| EventBus | `services/event_bus.py` | 300 | Event routing |
| EventStore | `services/event_store/` | 500 | Parquet persistence |
| LiveStateProvider | `services/live_state_provider.py` | 100 | Server-authoritative state |
| GameState | `core/game_state.py` | 640 | State container |

---

## Components to REMOVE

| Component | Files | LOC | Reason |
|-----------|-------|-----|--------|
| Chart widget | `widgets/chart.py` | 524 | Visual only |
| Timing overlay | `timing_overlay.py` | 334 | Visual only |
| Audio player | `audio_cue_player.py` | 251 | Sound effects |
| Debug terminal | `debug_terminal.py` | 280 | Debug only |
| Theme manager | `interactions/theme_manager.py` | ~150 | Visual only |
| 4 Dialogs | `*_dialog.py`, `bot_config_panel.py` | 1,600 | Config via file |
| Replay components | `replay_*.py` | ~600 | Not live training |
| 8 Handler mixins | `handlers/*.py` | ~1,100 | Replace with simple handlers |
| 5 Builders | `builders/*.py` | ~1,100 | Replace with inline code |
| MainWindow (current) | `main_window.py` | 721 | Replace with MinimalWindow |

**Net Result:**
- Current UI: ~8,700 LOC
- Minimal UI: ~500-600 LOC
- **~93% reduction in UI complexity**

---

## New File Structure

```
src/ui/
├── minimal_window.py      # NEW: Single-file minimal UI (~500 LOC)
├── controllers/
│   └── trading_controller.py  # KEEP: ButtonEvent emission
└── (everything else removed or archived)
```

---

## Implementation Tasks

### Task 1: Create MinimalWindow
- New file `src/ui/minimal_window.py`
- Plain Tk widgets, no mixins
- Status bar + controls layout
- Wire up EventBus subscriptions for status updates

### Task 2: Wire TradingController
- Reuse existing TradingController
- Connect button callbacks
- Verify ButtonEvent emission works

### Task 3: Wire WebSocket Event Handlers
- Subscribe to `gameStateUpdate` for TICK/PRICE/PHASE
- Subscribe to `usernameStatus` for USER
- Subscribe to `playerUpdate` for BALANCE
- Subscribe to `BridgeStatus` for CONNECTION

### Task 4: Update main.py
- Replace MainWindow instantiation with MinimalWindow
- Remove unused imports
- Verify startup works

### Task 5: Archive/Remove Old UI Files
- Move old UI files to `src/ui/_archived/` (or delete)
- Update any imports that reference removed files
- Run tests to verify nothing breaks

### Task 6: Test End-to-End
- Connect to browser
- Verify buttons click in browser
- Verify ButtonEvents emitted with timestamps
- Verify server ACKs captured
- Verify Parquet files written

---

## Success Criteria

- [ ] MinimalWindow displays all status fields
- [ ] All buttons functional (BUY, SELL, SIDEBET, percentages, increments)
- [ ] ButtonEvents emitted with client_ts on every button press
- [ ] Server ACKs (43XXXX) captured by CDPWebSocketInterceptor
- [ ] Latency data stored in Parquet
- [ ] UI code reduced to ~500-600 LOC
- [ ] All existing backend tests still pass

---

*Design approved: 2025-12-28*
