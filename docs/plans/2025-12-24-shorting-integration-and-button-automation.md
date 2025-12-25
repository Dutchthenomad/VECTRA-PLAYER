# Shorting Integration & Button Automation Planning

**Date**: December 24, 2025
**Status**: ⛔ SHORTING DEFERRED | Button automation ACTIVE
**Scope**: Button automation for known features (shorting removed from v1.0)

---

## ⚠️ DEFERRAL NOTICE (2025-12-24 Late Night)

**Shorting sections of this document are SPECULATIVE and NOT IMPLEMENTED.**

rugs-expert agent confirmed NO empirical data exists for shorting:
- `shortPosition` field always `null` in all WebSocket captures
- No `shortOrder` request/response events documented
- UI buttons and XPaths unknown
- All mechanics (leverage, liquidation, amounts) undocumented

**Decision**: Shorting removed from v1.0 scope. Research continues in claude-flow.
Only the **Button Automation** sections (Sections 5-7) remain active for v1.0.

---

## Overview

This document plans button automation for VECTRA-PLAYER's bot framework.
**Shorting sections are preserved for future reference but are NOT active.**

**Key Objectives**:
1. Document the shorting mechanic and WebSocket protocol
2. Extend EventStore schemas for short positions
3. Map ALL button XPaths for browser automation
4. Design confirmation monitoring for shorts
5. Plan toast notification system redesign (deferred)

---

## 1. Shorting Mechanic Documentation

### What is Shorting?

**Shorting in rugs.fun** is a bet that the price will GO DOWN (opposite of longs).

**Key Differences from Longs**:
- **Longs profit when price RISES** (buy low, sell high)
- **Shorts profit when price FALLS** (short high, cover low)
- **Liquidation risk** - shorts can be liquidated if price moves against you

### How Shorting Works

Based on the WebSocket events spec and schema v2.0.0:

#### 1. Entry (Short Open)
**Button**: SHORT (new button added to UI)
**Action**: Open a short position at current price
**Effect**: Creates a `shortPosition` object in `playerUpdate`

```json
{
  "shortPosition": {
    "qty": 0.05,           // Short position size (units)
    "avgCost": 10.5,       // Entry price
    "shortPnl": -0.002,    // Current P&L (negative = losing)
    "liquidationPrice": 15.0,
    "marginRatio": 0.6,
    "atRisk": false
  }
}
```

#### 2. Exit (Short Close)
**Button**: CLOSE SHORT (or partial close buttons)
**Action**: Close short position at current price
**Effect**: Position settled, P&L realized

#### 3. Liquidation Risk
**Condition**: Price moves too far against you
**Trigger**: `marginRatio` drops below threshold
**Effect**: Forced position close, loss of collateral

### WebSocket Events for Shorts

Based on the `WEBSOCKET_EVENTS_SPEC.md`:

#### `playerUpdate` with Short Fields

**Frequency**: After each short trade
**Auth Required**: Yes
**Key Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `shortPosition` | object/null | Active short position |
| `shortPosition.qty` | float | Short size (units) |
| `shortPosition.avgCost` | float | Entry price |
| `shortPosition.shortPnl` | float | Unrealized P&L |
| `shortPosition.liquidationPrice` | float | Price at which liquidation occurs |
| `shortPosition.marginRatio` | float | Margin health (0.0-1.0) |
| `shortPosition.atRisk` | bool | Liquidation warning flag |

**Example**:
```json
{
  "id": "did:privy:...",
  "cash": 3.967,
  "positionQty": 0.222,      // Long position
  "shortPosition": {          // NEW: Short position
    "qty": 0.05,
    "avgCost": 10.5,
    "shortPnl": -0.002,
    "liquidationPrice": 15.0,
    "marginRatio": 0.6,
    "atRisk": false
  }
}
```

#### `standard/newTrade` for Shorts

**Frequency**: When any player opens/closes a short
**Auth Required**: No
**Key Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"short_open"` or `"short_close"` |
| `qty` | float | Short size |
| `price` | float | Execution price |

**Example**:
```json
{
  "id": "trade-uuid",
  "gameId": "20251224-...",
  "playerId": "did:privy:...",
  "type": "short_open",      // NEW: Short trade type
  "qty": 0.05,
  "price": 10.5,
  "tickIndex": 42
}
```

#### Confirmation Events

**Short Open**:
- Request: `42425["shortOpen", {"amount": 0.05}]`
- Response: `43425[{"success": true, "executedPrice": 10.5}]`
- Confirmation: `playerUpdate` with `shortPosition` populated

**Short Close**:
- Request: `42426["shortClose", {"percentage": 100}]`
- Response: `43426[{"success": true, "executedPrice": 8.2}]`
- Confirmation: `playerUpdate` with `shortPosition = null`

### Detection Logic

**Has Active Short**:
```python
def has_short_position(player_update: dict) -> bool:
    short = player_update.get('shortPosition')
    return short is not None and short.get('qty', 0) > 0
```

**Short P&L Calculation**:
```python
def calculate_short_pnl(entry_price: float, current_price: float, qty: float) -> float:
    # Shorts profit when price DROPS
    price_change = entry_price - current_price  # Inverted from longs
    return price_change * qty
```

**Liquidation Risk**:
```python
def is_liquidation_risk(player_update: dict) -> bool:
    short = player_update.get('shortPosition')
    if not short:
        return False
    return short.get('atRisk', False) or short.get('marginRatio', 1.0) < 0.3
```

---

## 2. Schema Additions Needed

### ActionType Enum (Already Added)

The `player_action.py` schema already has:

```python
class ActionType(str, Enum):
    SHORT_OPEN = "SHORT_OPEN"
    SHORT_CLOSE = "SHORT_CLOSE"
```

**No changes needed** - schema v2.0.0 already includes shorts!

### Short Position State (Already Added)

The `short_position.py` model already has:

```python
class ShortPositionState(BaseModel):
    has_short: bool
    short_qty: Decimal
    short_entry_price: Decimal
    short_pnl: Decimal
    liquidation_price: Decimal | None = None
    margin_ratio: Decimal | None = None
    at_risk: bool = False
```

**No changes needed** - already implemented!

### Alert Types (Already Added)

The `alert_trigger.py` model already has:

```python
class AlertType(str, Enum):
    SHORT_ENTRY_SIGNAL = "SHORT_ENTRY_SIGNAL"
    SHORT_EXIT_SIGNAL = "SHORT_EXIT_SIGNAL"
    SHORT_LIQUIDATION_WARNING = "SHORT_LIQUIDATION_WARNING"
```

**No changes needed** - schema is future-proofed!

### Outstanding Work

**Integration Tasks**:
1. Add SHORT button selectors to `src/browser/dom/selectors.py`
2. Add short confirmation logic to ConfirmationMonitor
3. Update BotActionInterface to support short actions
4. Add short position tracking to LiveStateProvider

---

## 3. Button XPath Mapping

### Button Inventory

All buttons requiring XPath selectors:

| Button | Purpose | Phases | Notes |
|--------|---------|--------|-------|
| **BUY** | Open long position | PRESALE, ACTIVE | Already mapped |
| **SELL** | Close long position | ACTIVE | Already mapped |
| **SELL 10%** | Partial close (10%) | ACTIVE | Already mapped |
| **SELL 25%** | Partial close (25%) | ACTIVE | Already mapped |
| **SELL 50%** | Partial close (50%) | ACTIVE | Already mapped |
| **SELL 100%** | Full close | ACTIVE | Already mapped |
| **SIDEBET** | Place sidebet | ACTIVE | Already mapped |
| **SHORT** | Open short position | ACTIVE | **NEW - Needs mapping** |
| **CLOSE SHORT** | Close short position | ACTIVE | **NEW - Needs mapping** |
| **CLOSE SHORT 10%** | Partial short close | ACTIVE | **NEW - Needs mapping** |
| **CLOSE SHORT 25%** | Partial short close | ACTIVE | **NEW - Needs mapping** |
| **CLOSE SHORT 50%** | Partial short close | ACTIVE | **NEW - Needs mapping** |
| **CLOSE SHORT 100%** | Full short close | ACTIVE | **NEW - Needs mapping** |
| **BET INCREMENT +0.001** | Increase bet | All | Already mapped |
| **BET INCREMENT +0.01** | Increase bet | All | Already mapped |
| **BET INCREMENT +0.1** | Increase bet | All | Already mapped |
| **BET INCREMENT +1** | Increase bet | All | Already mapped |
| **BET CLEAR (X)** | Clear bet amount | All | Already mapped |
| **BET HALF (1/2)** | Halve bet amount | All | Already mapped |
| **BET DOUBLE (X2)** | Double bet amount | All | Already mapped |
| **BET MAX** | Set max bet | All | Already mapped |

### XPath Documentation Template

**Standard Format** (from existing `selectors.py`):

```python
# Button Name: <NAME>
# Purpose: <DESCRIPTION>
# Phases: <COOLDOWN/PRESALE/ACTIVE/RUGGED>
# Expected State: <ENABLED_WHEN>
# Confirmation Event: <WS_EVENT_NAME>
# Detection Logic: <HOW_TO_VERIFY>

<BUTTON_NAME>_SELECTORS = [
    # Primary: Rugs.fun specific class (preferred)
    'div[class*="_buttonSection_"]:nth-child(N)',
    '[class*="_buttonsRow_"] > div:nth-child(N)',

    # Regex text matching (handles dynamic text)
    "button >> text=/^<TEXT>/i",

    # Case-insensitive class patterns
    'button[class*="<class>" i]',

    # Structural fallback (position-based)
    '[class*="tradeControls"] button:nth-of-type(N)',

    # Data attributes
    '[data-action="<action>"]',
    '[data-testid="<button>-button"]',

    # Original fallback
    'button:has-text("<TEXT>")',
]
```

### New Short Button Selectors

Add to `src/browser/dom/selectors.py`:

```python
# ============================================================================
# SHORT POSITION BUTTON SELECTORS (New Feature - 2025-12-24)
# ============================================================================

# Button Name: SHORT
# Purpose: Open short position (bet price will go DOWN)
# Phases: ACTIVE
# Expected State: enabled when has_funds and no_existing_short
# Confirmation Event: playerUpdate
# Detection Logic: shortPosition.qty > 0

SHORT_BUTTON_SELECTORS = [
    # Primary: Rugs.fun specific class (TBD - needs live inspection)
    'div[class*="_shortButton_"]',
    '[class*="_buttonsRow_"] > div:nth-child(3)',  # Position TBD

    # Regex text matching
    "button >> text=/^SHORT/i",
    "button >> text=/^SELL SHORT/i",

    # Case-insensitive class patterns
    'button[class*="short" i]',
    'button[class*="Short" i]',

    # Data attributes
    '[data-action="short"]',
    '[data-action="short-open"]',
    '[data-testid="short-button"]',

    # Original fallback
    'button:has-text("SHORT")',
    'button:has-text("Short")',
    'button:has-text("SELL SHORT")',
]

# Button Name: CLOSE SHORT
# Purpose: Close short position (full or partial)
# Phases: ACTIVE
# Expected State: enabled when has_short_position
# Confirmation Event: playerUpdate
# Detection Logic: shortPosition = null (full close) or qty decreased (partial)

CLOSE_SHORT_BUTTON_SELECTORS = [
    # Primary: Rugs.fun specific class (TBD - needs live inspection)
    'div[class*="_closeShortButton_"]',
    '[class*="_shortControlButtons_"] button:nth-child(1)',

    # Regex text matching
    "button >> text=/^CLOSE/i",
    "button >> text=/^COVER/i",

    # Case-insensitive class patterns
    'button[class*="closeShort" i]',
    'button[class*="cover" i]',

    # Data attributes
    '[data-action="short-close"]',
    '[data-action="cover-short"]',
    '[data-testid="close-short-button"]',

    # Original fallback
    'button:has-text("CLOSE SHORT")',
    'button:has-text("Close Short")',
    'button:has-text("COVER")',
]

# Partial Short Close Buttons (10%, 25%, 50%, 100%)
# Similar to SELL partial buttons but for shorts

SHORT_PERCENTAGE_10_SELECTORS = [
    'button[class*="_shortPercentageBtn_"]:nth-child(1)',
    '[class*="_shortControlButtons_"] button:nth-child(1)',
    "button >> text=/^10%/i",
    '[data-percentage="10%"][data-action="short-close"]',
]

SHORT_PERCENTAGE_25_SELECTORS = [
    'button[class*="_shortPercentageBtn_"]:nth-child(2)',
    '[class*="_shortControlButtons_"] button:nth-child(2)',
    "button >> text=/^25%/i",
    '[data-percentage="25%"][data-action="short-close"]',
]

SHORT_PERCENTAGE_50_SELECTORS = [
    'button[class*="_shortPercentageBtn_"]:nth-child(3)',
    '[class*="_shortControlButtons_"] button:nth-child(3)',
    "button >> text=/^50%/i",
    '[data-percentage="50%"][data-action="short-close"]',
]

SHORT_PERCENTAGE_100_SELECTORS = [
    'button[class*="_shortPercentageBtn_"]:nth-child(4)',
    '[class*="_shortControlButtons_"] button:nth-child(4)',
    "button >> text=/^100%/i",
    '[data-percentage="100%"][data-action="short-close"]',
]
```

---

## 4. Automation Strategy

### Button Click vs HTTP POST

**Question**: Should Puppeteer click buttons or intercept HTTP POST?

**Analysis**:

| Method | Pros | Cons |
|--------|------|------|
| **Button Click** | Realistic user behavior, handles UI state changes, no reverse engineering | Slower (~100-200ms overhead), subject to UI bugs |
| **HTTP POST Interception** | Faster (~50ms), bypasses UI entirely | Fragile (protocol changes break bot), harder to debug, may trigger anti-bot detection |

**Recommendation**: **Button Click** (current approach)

**Rationale**:
1. **Robustness** - UI changes are visible, HTTP changes are not
2. **Debugging** - Can visually see what failed
3. **Future-proofing** - Less likely to break on backend updates
4. **Detection avoidance** - Looks like real user traffic

**Optimization**: Use CDP for WebSocket interception but Puppeteer for button clicks

### Selector Strategy (Already Implemented)

The current `selectors.py` uses a **cascading fallback** approach:

1. **Rugs.fun specific classes** (e.g., `div[class*="_buttonSection_"]`)
2. **Regex text matching** (e.g., `text=/^BUY/i`)
3. **Case-insensitive class matching** (e.g., `button[class*="buy" i]`)
4. **Structural position** (e.g., `nth-child(1)`)
5. **Data attributes** (e.g., `[data-action="buy"]`)
6. **Text fallback** (e.g., `button:has-text("BUY")`)

**This is ideal** - try specific selectors first, fall back to generic ones.

---

## 5. Confirmation Monitoring

### Current System (from `confirmation-mapping.md`)

| Action | Confirmation Event | Detection |
|--------|-------------------|-----------|
| BUY | `playerUpdate` | positionQty ↑, cash ↓ |
| SELL | `playerUpdate` | positionQty ↓, cash ↑ |
| SIDEBET | `currentSidebet` | type == "placed" |

### Short Confirmation Logic

**Short Open**:
```python
def confirm_short_open(action_id: str, player_update: dict) -> bool:
    """Confirm short position opened."""
    short = player_update.get('shortPosition')
    if not short:
        return False

    # Check that short position exists and has quantity
    return short.get('qty', 0) > 0
```

**Short Close (Full)**:
```python
def confirm_short_close_full(action_id: str, player_update: dict) -> bool:
    """Confirm short position fully closed."""
    short = player_update.get('shortPosition')

    # Full close = shortPosition is null or qty = 0
    return short is None or short.get('qty', 0) == 0
```

**Short Close (Partial)**:
```python
def confirm_short_close_partial(
    action_id: str,
    player_update: dict,
    before_qty: Decimal,
    percentage: Decimal
) -> bool:
    """Confirm partial short close."""
    short = player_update.get('shortPosition')
    if not short:
        return False  # Position fully closed (unexpected)

    after_qty = Decimal(str(short.get('qty', 0)))
    expected_qty = before_qty * (1 - percentage)

    # Allow 1% tolerance for rounding
    tolerance = before_qty * Decimal('0.01')
    return abs(after_qty - expected_qty) <= tolerance
```

---

## 6. Toast Notification Redesign (DEFERRED)

**Status**: Outlined for future implementation

### New Event-Driven Design

**Architecture**:
```
EventStore → AlertTrigger → EventBus → ToastManager → UI
```

### Alert Types for Shorts

Already defined in `alert_trigger.py`:

```python
class AlertType(str, Enum):
    SHORT_ENTRY_SIGNAL = "SHORT_ENTRY_SIGNAL"
    SHORT_EXIT_SIGNAL = "SHORT_EXIT_SIGNAL"
    SHORT_LIQUIDATION_WARNING = "SHORT_LIQUIDATION_WARNING"
```

---

## 7. Implementation Roadmap

### Phase 1: Short Button Selectors (1 day)
1. Chrome DevTools inspection
2. Add SHORT_BUTTON_SELECTORS to `selectors.py`
3. Manual verification with Puppeteer

### Phase 2: Confirmation Monitoring (2 days)
1. Add short confirmation logic
2. Update confirmation-mapping.md
3. Add latency tracking

### Phase 3: BotActionInterface Integration (2 days)
1. Extend BotActionInterface with short methods
2. Add short position tracking to LiveStateProvider
3. Integration tests

---

## 8. Chrome DevTools Inspection Checklist

Use `mcp__chrome-devtools__*` tools to:

1. Navigate to https://rugs.fun
2. Take DOM snapshot (depth=5)
3. Identify SHORT button elements
4. Capture class names, data attributes, text content
5. Test button states (enabled/disabled)
6. Document actual selectors

---

## 9. Deliverables Summary

1. **Shorting Mechanic Documentation** ✅
2. **ActionType Additions** ✅ (already in schema v2.0.0)
3. **Button XPath Template** ✅
4. **Button Inventory** ✅ (24 buttons, 12 new for shorts)
5. **Automation Strategy** ✅ (button click recommended)
6. **Toast Scope** ✅ (deferred, event-driven design outlined)

---

**End of Planning Document**
