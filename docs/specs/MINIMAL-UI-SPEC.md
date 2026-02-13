# MINIMAL-UI-SPEC: Tkinter to HTML Conversion Specification

**Status:** CANONICAL | **Version:** 1.0.0 | **Date:** 2026-01-24

---

## Purpose

This specification defines the complete structure, behavior, and styling of the Tkinter `MinimalWindow` UI component, enabling precise recreation in HTML/CSS/JavaScript or any other UI framework.

**Source:** `src/ui/minimal_window.py` (1,107 lines)

---

## HTML Artifact Exclusions

The following Tkinter components are **excluded** from the HTML artifact implementation:

| Component | Reason | Alternative |
|-----------|--------|-------------|
| **Recording Toggle** | Recording is handled by the Recording Service (`services/recording/`) | Server-side recording via Foundation subscriber |

These exclusions maintain separation of concerns - HTML artifacts are display/interaction layers, not data persistence layers.

---

## 1. Visual Layout Blueprint

### Window Configuration

| Property | Value |
|----------|-------|
| Initial Size | 900 x 200 pixels |
| Minimum Size | 800 x 180 pixels |
| Background | #1a1a1a |
| Padding | 10px all sides |

### Layout Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ ROOT WINDOW (900x200, min 800x180, bg: #1a1a1a, padding: 10px)                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ MAIN FRAME (fill: both, expand: true)                                           │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ STATUS BAR - Row 1 (fill: x, pady: 2)                                       │ │
│ │ ┌──────────┬──────────┬──────────┬────────────┬───────────────────────────┐ │ │
│ │ │ TICK:    │ PRICE:   │ PHASE:   │ [REC]      │ CONNECTION: ● [CONNECT]   │ │ │
│ │ │ 0000     │ 0000.00  │ UNKNOWN  │ toggle     │              [EXECUTE]    │ │ │
│ │ │ (LEFT)   │ (LEFT)   │ (LEFT)   │ (LEFT)     │              (RIGHT)      │ │ │
│ │ └──────────┴──────────┴──────────┴────────────┴───────────────────────────┘ │ │
│ │                                                                             │ │
│ │ STATUS BAR - Row 2 (fill: x, pady: 2)                                       │ │
│ │ ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ USER: ---                                          BALANCE: 00.000 SOL  │ │ │
│ │ │ (LEFT)                                                        (RIGHT)   │ │ │
│ │ └─────────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ─────────────────────────────── SEPARATOR ────────────────────────────────────  │
│ (height: 1px, bg: #666666, fill: x, pady: 5)                                    │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ CONTROLS (fill: x, pady: 5)                                                 │ │
│ │ ┌────────┬─────────────────────────────────────────────────┬──────────────┐ │ │
│ │ │ PCT    │ CENTER CONTROLS                                 │ ACTION      │ │ │
│ │ │ FRAME  │ (fill: x, expand: true)                         │ FRAME       │ │ │
│ │ │        │                                                 │             │ │ │
│ │ │ [10%]  │  [+0.001] [+0.01] [+0.1] [+1]  |  [1/2] [X2] [MAX]  │   [BUY]     │ │ │
│ │ │ [25%]  │  ─────────────────────────────────────────────  │  [SIDEBET]  │ │ │
│ │ │ [50%]  │  BET AMOUNT  [X]  [____0.000____]  SOL          │   [SELL]    │ │ │
│ │ │[100%]* │                                                 │             │ │ │
│ │ └────────┴─────────────────────────────────────────────────┴──────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Color Palette

### Core Colors

```css
:root {
  /* Background colors */
  --bg-primary: #1a1a1a;      /* Main window background */
  --bg-panel: #2a2a2a;        /* Panel/input backgrounds */
  --bg-separator: #666666;    /* Separator line */

  /* Text colors */
  --text-primary: #ffffff;    /* Primary text */
  --text-dim: #888888;        /* Dim labels */

  /* Status colors */
  --color-green: #00ff66;     /* Active/positive/connected */
  --color-yellow: #ffcc00;    /* Warning/presale */
  --color-blue: #3399ff;      /* Neutral buttons */
  --color-gray: #666666;      /* Disabled/unselected */
  --color-selected: #00cc66;  /* Selected state */

  /* Error colors */
  --color-red-error: #cc3333; /* Error/disabled toggle */
  --color-red-press: #ff4444; /* Active press state */
  --color-red-phase: #ff3366; /* Cooldown/rugged phase */

  /* Button hover colors */
  --hover-green: #00cc55;
  --hover-yellow: #ddaa00;
  --hover-blue: #2277dd;
}
```

### Phase Color Mapping

| Phase | Color Variable | Hex Value |
|-------|---------------|-----------|
| ACTIVE | --color-green | #00ff66 |
| PRESALE | --color-yellow | #ffcc00 |
| COOLDOWN | --color-red-phase | #ff3366 |
| RUGGED | --color-red-phase | #ff3366 |
| UNKNOWN | --text-primary | #ffffff |

---

## 3. Typography

| Element | Font Family | Size | Weight |
|---------|-------------|------|--------|
| Labels (dim) | Arial | 10pt | normal |
| Values | Arial | 10pt | bold |
| Buttons (small) | Arial | 9pt | bold |
| Buttons (action) | Arial | 14pt | bold |
| Bet entry | Arial | 12pt | normal |
| Recording status | Consolas | 8pt | normal |

---

## 4. Component Specifications

### 4.1 Status Bar - Row 1

#### TICK Display
```html
<div class="status-item">
  <span class="status-label">TICK:</span>
  <span class="status-value" id="tick-value">0000</span>
</div>
```

| Property | Value |
|----------|-------|
| Label color | #888888 |
| Value color | #ffffff |
| Value format | `{tick:04d}` (zero-padded 4 digits) |
| Update source | `game.tick` event → `data.tickCount` |

#### PRICE Display
```html
<div class="status-item">
  <span class="status-label">PRICE:</span>
  <span class="status-value" id="price-value">0000.00</span>
</div>
```

| Property | Value |
|----------|-------|
| Label color | #888888 |
| Value color | #ffffff |
| Value format | `{price:.2f}` (2 decimal places) |
| Update source | `game.tick` event → `data.price` or `data.multiplier` |

#### PHASE Display
```html
<div class="status-item">
  <span class="status-label">PHASE:</span>
  <span class="status-value status-phase" id="phase-value">UNKNOWN</span>
</div>
```

| Property | Value |
|----------|-------|
| Label color | #888888 |
| Value color | Dynamic (see Phase Color Mapping) |
| Values | UNKNOWN, ACTIVE, PRESALE, COOLDOWN, RUGGED |
| Update source | `game.tick` event → derived from multiple fields |

#### Recording Toggle (Conditional)
```html
<div class="recording-toggle" id="recording-toggle">
  <span class="rec-status">OFF</span>
  <button class="rec-button">REC</button>
</div>
```

| Property | Value |
|----------|-------|
| Status text (recording) | `"{event_count} | {game_id_short}"` |
| Status text (off) | "OFF" |
| Button color (recording) | #cc3333 (red) |
| Button color (off) | #666666 (gray) |
| Font | Consolas 8pt |

#### Connection Indicator
```html
<div class="connection-status">
  <span class="status-label">CONNECTION:</span>
  <span class="connection-dot" id="connection-dot">●</span>
  <button class="connect-btn" id="connect-btn">CONNECT</button>
</div>
```

| Property | Connected | Disconnected |
|----------|-----------|--------------|
| Dot color | #00ff66 | #666666 |
| Button text | "CONNECTED" | "CONNECT" |
| Button color | #00ff66 | #3399ff |
| Button enabled | false | true |

#### Execute Toggle
```html
<button class="execute-toggle" id="execute-toggle">EXECUTE: OFF</button>
```

| State | Text | Background |
|-------|------|------------|
| OFF | "EXECUTE: OFF" | #cc3333 |
| ON | "EXECUTE: ON" | #00cc55 |
| NO BROWSER | "EXECUTE: NO BROWSER" | #cc3333 |

### 4.2 Status Bar - Row 2

#### User Display
```html
<div class="user-info">
  <span class="status-label">USER:</span>
  <span class="status-value" id="user-value">---</span>
</div>
```

| Property | Value |
|----------|-------|
| Default | "---" |
| Update source | `connection.authenticated` event → `data.username` |

#### Balance Display
```html
<div class="balance-info">
  <span class="status-label">BALANCE:</span>
  <span class="balance-value" id="balance-value">00.000 SOL</span>
</div>
```

| Property | Value |
|----------|-------|
| Color | #00ff66 (green) |
| Format | `{balance:.3f} SOL` |
| Update source | `player.state` event → `data.cash` |

### 4.3 Percentage Buttons (Vertical Stack)

```html
<div class="pct-buttons">
  <button class="pct-btn" data-value="0.1">10%</button>
  <button class="pct-btn" data-value="0.25">25%</button>
  <button class="pct-btn" data-value="0.5">50%</button>
  <button class="pct-btn selected" data-value="1.0">100%</button>
</div>
```

| Property | Value |
|----------|-------|
| Width | 5ch |
| Height | 1.5em |
| Spacing | 2px vertical |
| Font | Arial 9pt bold |
| Default selected | 100% |

| State | Background | Border | Relief |
|-------|------------|--------|--------|
| Unselected | #666666 | 2px | raised |
| Selected | #00cc66 | 3px | sunken |
| Hover | #00cc66 | - | - |

**Behavior:** Radio-button style - only one selected at a time.

### 4.4 Increment Buttons (Horizontal Row)

```html
<div class="inc-buttons">
  <button class="inc-btn" data-amount="0.001">+0.001</button>
  <button class="inc-btn" data-amount="0.01">+0.01</button>
  <button class="inc-btn" data-amount="0.1">+0.1</button>
  <button class="inc-btn" data-amount="1">+1</button>
</div>
```

| Property | Value |
|----------|-------|
| Width | 6ch |
| Spacing | 3px horizontal |
| Background | #2a2a2a |
| Text color | #ffffff |
| Font | Arial 9pt |
| Hover | #666666 |

### 4.5 Utility Buttons (Horizontal Row)

```html
<div class="util-buttons">
  <button class="util-btn" id="btn-half">1/2</button>
  <button class="util-btn" id="btn-double">X2</button>
  <button class="util-btn" id="btn-max">MAX</button>
</div>
```

| Property | Value |
|----------|-------|
| Width | 6ch |
| Spacing | 3px horizontal |
| Background | #2a2a2a |
| Text color | #ffffff |
| Font | Arial 9pt |
| Hover | #666666 |

**Behavior:**
- **1/2**: Divide bet amount by 2
- **X2**: Multiply bet amount by 2
- **MAX**: Set bet amount to current balance

### 4.6 Bet Amount Entry

```html
<div class="bet-entry-row">
  <span class="bet-label">BET AMOUNT</span>
  <button class="clear-btn" id="btn-clear">X</button>
  <input type="text" class="bet-input" id="bet-entry" value="0.000">
  <span class="bet-unit">SOL</span>
</div>
```

#### Input Field
| Property | Value |
|----------|-------|
| Width | 12ch |
| Background | #2a2a2a |
| Text color | #ffffff |
| Font | Arial 12pt |
| Relief | sunken |
| Initial value | "0.000" |

#### Clear Button (X)
| Property | Value |
|----------|-------|
| Width | 3ch |
| Background | #cc3333 |
| Hover | #ff4444 |
| Font | Arial 10pt bold |

### 4.7 Action Buttons (Vertical Stack)

```html
<div class="action-buttons">
  <button class="action-btn buy-btn" id="btn-buy">BUY</button>
  <button class="action-btn sidebet-btn" id="btn-sidebet">SIDEBET</button>
  <button class="action-btn sell-btn" id="btn-sell">SELL</button>
</div>
```

| Property | All Buttons |
|----------|-------------|
| Width | 10ch |
| Height | 2 lines (~40px) |
| Spacing | 5px vertical |
| Font | Arial 14pt bold |
| Border | 2px raised |

| Button | Background | Text | Hover |
|--------|------------|------|-------|
| BUY | #00ff66 | #000000 | #00cc55 |
| SIDEBET | #ffcc00 | #000000 | #ddaa00 |
| SELL | #3399ff | #ffffff | #2277dd |

---

## 5. State Management

### 5.1 Application State

```javascript
const state = {
  // Game state (from WebSocket game.tick)
  tick: 0,
  price: 1.0,
  phase: "UNKNOWN",
  gameId: null,

  // Player state (from WebSocket player.state, AUTH required)
  username: "---",
  balance: 0.0,
  positionQty: 0.0,
  avgCost: 1.0,

  // Connection state
  connected: false,
  authenticated: false,

  // UI state (local)
  executionEnabled: false,
  isRecording: false,
  selectedPercentage: 1.0,
  betAmount: "0.000",

  // Sequence tracking (for ButtonEvent)
  sequenceId: null,
  sequencePosition: 0,
  lastActionTick: 0
};
```

### 5.2 State Update Sources

| State Field | Event Type | Data Path |
|-------------|------------|-----------|
| tick | game.tick | data.tickCount |
| price | game.tick | data.price OR data.multiplier |
| phase | game.tick | derived (see Phase Detection) |
| gameId | game.tick | data.gameId |
| username | connection.authenticated | data.username |
| balance | player.state | data.cash |
| positionQty | player.state | data.positionQty |
| connected | connection | data.connected |

---

## 6. Event Handling

### 6.1 WebSocket Event Subscriptions

```javascript
client.on('game.tick', (event) => {
  state.tick = event.data.tickCount;
  state.price = event.data.price ?? event.data.multiplier;
  state.phase = detectPhase(event.data);
  state.gameId = event.data.gameId;
  updateStatusBar();
});

client.on('player.state', (event) => {
  state.balance = event.data.cash;
  state.positionQty = event.data.positionQty;
  updateBalanceDisplay();
});

client.on('connection.authenticated', (event) => {
  state.username = event.data.username;
  state.authenticated = true;
  updateUserDisplay();
});

client.on('connection', (event) => {
  state.connected = event.connected;
  updateConnectionIndicator();
});
```

### 6.2 Phase Detection Logic

```javascript
function detectPhase(data) {
  if (data.cooldownTimer > 0) return "COOLDOWN";
  if (data.rugged && !data.active) return "RUGGED";
  if (data.allowPreRoundBuys) return "PRESALE";
  if (data.active && !data.rugged) return "ACTIVE";
  return "UNKNOWN";
}

function getPhaseColor(phase) {
  switch (phase) {
    case "ACTIVE": return "var(--color-green)";
    case "PRESALE": return "var(--color-yellow)";
    case "COOLDOWN":
    case "RUGGED": return "var(--color-red-phase)";
    default: return "var(--text-primary)";
  }
}
```

### 6.3 Button Click Handlers

Each button click:
1. Creates a ButtonEvent with current game context
2. Emits the event (for recording/logging)
3. Performs the button-specific action
4. Updates local UI state

```javascript
function onButtonClick(buttonText) {
  const event = createButtonEvent(buttonText);
  emitButtonEvent(event);
  performButtonAction(buttonText);
  updateUI();
}
```

---

## 7. ButtonEvent Schema

### 7.1 Full Schema

```javascript
{
  // Timestamps
  ts: "2026-01-24T10:30:45.123Z",  // ISO 8601 UTC
  server_ts: null,                 // Set by server on receipt
  client_timestamp: 1706096245123, // Unix ms

  // Button identification
  button_id: "BUY",                // See Button ID Mapping
  button_category: "action",       // action | bet_adjust | percentage

  // Game context (from state at click time)
  tick: 145,
  price: 2.35,
  game_phase: 2,                   // 0=COOLDOWN, 1=PRESALE, 2=ACTIVE, 3=RUGGED
  game_id: "20260124-abc123",

  // Player context
  balance: 10.5,
  position_qty: 2.0,
  bet_amount: 0.5,

  // Sequence tracking
  sequence_id: "uuid-v4-here",
  sequence_position: 0,
  ticks_since_last_action: 12,

  // Position tracking (for latency analysis)
  time_in_position: 0              // ticks held if in position
}
```

### 7.2 Button ID Mapping

| Button Text | button_id | button_category |
|-------------|-----------|-----------------|
| BUY | BUY | action |
| SELL | SELL | action |
| SIDEBET | SIDEBET | action |
| X | CLEAR | bet_adjust |
| +0.001 | INC_001 | bet_adjust |
| +0.01 | INC_01 | bet_adjust |
| +0.1 | INC_10 | bet_adjust |
| +1 | INC_1 | bet_adjust |
| 1/2 | HALF | bet_adjust |
| X2 | DOUBLE | bet_adjust |
| MAX | MAX | bet_adjust |
| 10% | SELL_10 | percentage |
| 25% | SELL_25 | percentage |
| 50% | SELL_50 | percentage |
| 100% | SELL_100 | percentage |

### 7.3 Game Phase Enum

| Phase | Numeric Value |
|-------|---------------|
| COOLDOWN | 0 |
| PRESALE | 1 |
| ACTIVE | 2 |
| RUGGED | 3 |

---

## 8. Sequence Management

### 8.1 Sequence Rules

- **New sequence starts when:**
  - ACTION button pressed (BUY, SELL, SIDEBET)
  - OR more than 50 ticks since last action (timeout)

- **Within a sequence:**
  - `sequence_position` increments for each button press
  - Same `sequence_id` maintained

### 8.2 Implementation

```javascript
class SequenceTracker {
  constructor() {
    this.sequenceId = crypto.randomUUID();
    this.sequencePosition = 0;
    this.lastActionTick = 0;
  }

  update(buttonCategory, currentTick) {
    const ticksSince = currentTick - this.lastActionTick;

    // New sequence if ACTION button or timeout
    if (buttonCategory === "action" || ticksSince > 50) {
      this.sequenceId = crypto.randomUUID();
      this.sequencePosition = 0;
    } else {
      this.sequencePosition++;
    }

    this.lastActionTick = currentTick;

    return {
      sequenceId: this.sequenceId,
      sequencePosition: this.sequencePosition,
      ticksSinceLastAction: Math.max(0, ticksSince)
    };
  }
}
```

---

## 9. CSS Class Reference

### Layout Classes
| Class | Purpose |
|-------|---------|
| `.minimal-trading` | Root container |
| `.main-frame` | Main content frame |
| `.status-bar` | Status bar container |
| `.status-row` | Individual status row |
| `.controls` | Controls section container |
| `.separator` | Horizontal separator line |

### Status Classes
| Class | Purpose |
|-------|---------|
| `.status-item` | Label + value pair |
| `.status-label` | Dim label text |
| `.status-value` | Bold value text |
| `.status-phase` | Phase value (dynamic color) |
| `.connection-dot` | Connection indicator dot |
| `.balance-value` | Balance display (green) |

### Button Classes
| Class | Purpose |
|-------|---------|
| `.pct-btn` | Percentage button |
| `.pct-btn.selected` | Selected percentage |
| `.inc-btn` | Increment button |
| `.util-btn` | Utility button |
| `.action-btn` | Action button (large) |
| `.buy-btn` | BUY button (green) |
| `.sidebet-btn` | SIDEBET button (yellow) |
| `.sell-btn` | SELL button (blue) |
| `.clear-btn` | Clear (X) button (red) |
| `.connect-btn` | Connect button |
| `.execute-toggle` | Execute toggle |

### State Classes
| Class | Purpose |
|-------|---------|
| `.connected` | Connected state |
| `.disconnected` | Disconnected state |
| `.recording` | Recording active |
| `.selected` | Selected button |
| `.disabled` | Disabled state |

---

## 10. Accessibility

### Keyboard Navigation
- Tab through all interactive elements
- Enter/Space to activate buttons
- Arrow keys within button groups

### ARIA Attributes
```html
<button class="pct-btn" role="radio" aria-checked="false">10%</button>
<span class="connection-dot" role="status" aria-live="polite">●</span>
<input class="bet-input" aria-label="Bet amount in SOL">
```

---

## 11. Responsive Behavior

### Minimum Width (800px)
- All controls remain visible
- Button text may truncate
- Spacing reduced

### Default Width (900px)
- Full spacing
- All text visible
- Optimal layout

### Width > 900px
- Center section expands
- Action buttons maintain fixed size
- Percentage buttons maintain fixed width

---

## 12. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-24 | Initial specification |

---

## 13. References

| Document | Purpose |
|----------|---------|
| `src/ui/minimal_window.py` | Source implementation |
| `src/ui/controllers/trading_controller.py` | ButtonEvent emission |
| `docs/specs/MODULE-EXTENSION-SPEC.md` | HTML artifact requirements |
| `src/artifacts/shared/foundation-ws-client.js` | WebSocket client |
| `src/artifacts/shared/vectra-styles.css` | Theme CSS variables |
