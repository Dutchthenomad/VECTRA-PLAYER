# Socket Deprecation & UI Refactoring Cleanup Plan

**Created:** December 23, 2025
**Branch:** `claude/cleanup-deprecated-socket-logic-PDwKv`
**Status:** Planning Complete - Ready for Execution

---

## Executive Summary

Since Phase 12C integrated LiveStateProvider for server-authoritative state via WebSockets, several legacy systems are now deprecated but not yet removed. This plan consolidates the cleanup of:

1. **Button state control** (missing - needs implementation)
2. **Toast notification systems** (duplicate implementations - needs consolidation)
3. **Local balance validation** (deprecated - should use LiveStateProvider)
4. **GameState for live mode** (deprecated - should be replay-only)

---

## Current State Analysis

### ✅ What's Working (Phase 12C Complete)

- LiveStateProvider receives `playerUpdate` WebSocket events
- Balance display uses LiveStateProvider when connected
- Server state reconciliation active
- EventStore captures all events to Parquet
- State drift detection implemented

### ❌ What's Broken/Deprecated

1. **Button State Control: MISSING**
   - Location: `src/ui/builders/action_builder.py:89, 100, 111`
   - Issue: All buttons hardcoded to `state=tk.NORMAL` (always enabled)
   - Impact: Users can click BUY/SELL/SIDEBET even when server would reject
   - Browser click happens BEFORE validation (lines 120-126 in trading_controller.py)

2. **Toast Notifications: FRAGMENTED**
   - Two implementations:
     - `src/ui/widgets/toast_notification.py` (79 lines, Toplevel-based)
   - Issues:
     - BotManager crashes calling `toast.show()` with invalid `bootstyle` kwarg
     - API incompatibility between implementations

3. **Local Balance Validation: DEPRECATED**
   - Location: `src/ui/controllers/trading_controller.py:363, 390-392`
   - Issue: Checks `self.state.get("balance")` instead of `live_state_provider.cash`
   - Impact: Can drift from server truth, validation may be stale

4. **GameState for Live Mode: DEPRECATED**
   - Location: `src/core/game_state.py` (990 lines)
   - Issue: Still used for live mode decisions, should be replay-only
   - Impact: Dual state system creates confusion, reconciliation overhead

---

## Migration Plan

### Phase 1: Implement Button State Control (Server-Authoritative)

**Goal:** Add dynamic button enable/disable logic using LiveStateProvider

**Files to Modify:**
- `src/ui/builders/action_builder.py` - Add state parameter to builder
- `src/ui/main_window.py` - Wire LiveStateProvider to button updates
- `src/ui/handlers/player_handlers.py` - Update buttons on PLAYER_UPDATE events

**Implementation:**

```python
# action_builder.py - Add update method
class ActionBuilder:
    def update_button_states(self, live_provider: LiveStateProvider, game_active: bool):
        """Update button states based on server state."""
        # SIDEBET: Enabled if connected, has balance, no active sidebet, game active
        can_sidebet = (
            live_provider.is_connected and
            live_provider.cash >= min_bet and
            not has_active_sidebet and  # Need to track this
            game_active
        )
        self.sidebet_button.config(state=tk.NORMAL if can_sidebet else tk.DISABLED)

        # BUY: Enabled if connected, has balance, game active
        can_buy = (
            live_provider.is_connected and
            live_provider.cash >= min_bet and
            game_active
        )
        self.buy_button.config(state=tk.NORMAL if can_buy else tk.DISABLED)

        # SELL: Enabled if connected, has position
        can_sell = (
            live_provider.is_connected and
            live_provider.has_position
        )
        self.sell_button.config(state=tk.NORMAL if can_sell else tk.DISABLED)
```

**Event Wiring:**
- Subscribe to `Events.PLAYER_UPDATE` → update buttons
- Subscribe to `Events.GAME_TICK` → update game_active state
- Subscribe to `Events.WS_SOURCE_CHANGED` → update connection state

**Tests to Add:**
- `test_button_states_update_on_player_update()`
- `test_sidebet_disabled_when_insufficient_balance()`
- `test_sell_disabled_when_no_position()`
- `test_all_buttons_disabled_when_disconnected()`

---

### Phase 2: Consolidate Toast Notification System

**Goal:** Single, socket-driven notification system

**Decision:** Keep `ui/widgets/toast_notification.py` (simpler), remove `ui/toast_notification.py`

**Files to Modify:**
- `src/ui/widgets/toast_notification.py` - Add socket event handlers
- `src/ui/main_window.py` - Wire socket events to toasts
- `src/bot/bot_controller.py` - Fix invalid `bootstyle` kwarg

**Socket Events to Wire:**

```python
# Wire these WebSocket events to toasts
Events.TRADE_CONFIRMED → "Trade confirmed!" (success)
Events.TRADE_REJECTED → "Trade rejected: {reason}" (error)
Events.INSUFFICIENT_BALANCE → "Insufficient balance" (error)
Events.SIDEBET_PLACED → "Sidebet placed: {amount} SOL" (warning)
Events.SIDEBET_RESOLVED → "Sidebet {won|lost}: {amount} SOL" (success/error)
Events.RUG_DETECTED → "RUG DETECTED!" (error)
Events.GAME_STARTED → "Game started" (info)
Events.GAME_ENDED → "Game ended" (info)
```

**Migration:**
1. Add event subscription method to ToastNotification
2. Subscribe to events in MainWindow init
4. Update all callers to use unified toast

**Tests to Add:**
- `test_toast_shows_on_trade_confirmed()`
- `test_toast_shows_on_trade_rejected()`
- `test_toast_shows_on_insufficient_balance()`

---

### Phase 3: Replace Local Balance Validation with LiveStateProvider

**Goal:** Use server-authoritative balance for all validation

**Files to Modify:**
- `src/ui/controllers/trading_controller.py:363, 390-392`

**Changes:**

```python
# OLD (trading_controller.py:363, 390-392)
balance = self.state.get("balance")
if bet_amount > balance:
    self.toast.show(f"Insufficient balance! Have {balance:.4f} SOL", "error")
    return None

# NEW
# Check if we have LiveStateProvider (live mode)
if hasattr(self.parent, 'live_state_provider') and self.parent.live_state_provider.is_connected:
    balance = self.parent.live_state_provider.cash
else:
    # Fallback to GameState for replay mode
    balance = self.state.get("balance")

if bet_amount > balance:
    self.toast.show(f"Insufficient balance! Have {balance:.4f} SOL", "error")
    return None
```

**Similar changes needed in:**
- `max_bet_amount()` method (line 363)
- `get_bet_amount()` validation (line 390-392)

**Tests to Add:**
- `test_validation_uses_live_provider_when_connected()`
- `test_validation_falls_back_to_gamestate_in_replay()`

---

### Phase 4: Deprecate GameState for Live Mode

**Goal:** Make GameState replay-only, use LiveStateProvider exclusively in live mode

**Files to Modify:**
- `src/ui/main_window.py` - Add mode-aware state accessor
- `src/core/trade_manager.py` - Check mode before updating GameState
- `src/ui/handlers/balance_handlers.py` - Use LiveStateProvider in live mode

**Implementation:**

```python
# main_window.py - Add helper method
def get_current_balance(self) -> Decimal:
    """Get balance from appropriate source based on mode."""
    if self.live_mode and self.live_state_provider.is_connected:
        return self.live_state_provider.cash
    else:
        return self.state.get("balance")

def get_current_position(self) -> dict:
    """Get position from appropriate source based on mode."""
    if self.live_mode and self.live_state_provider.is_connected:
        if self.live_state_provider.has_position:
            return {
                "amount": self.live_state_provider.position_qty,
                "entry_price": self.live_state_provider.avg_cost,
                "status": "active"
            }
        return None
    else:
        return self.state.get("position")
```

**Add Deprecation Warnings:**
```python
# game_state.py - Add to methods used in live mode
def update_balance(self, amount: Decimal, reason: str = "") -> bool:
    if self._is_live_mode():
        logger.warning(
            "GameState.update_balance() called in live mode - "
            "should use LiveStateProvider instead"
        )
    # ... rest of method
```

**Tests to Add:**
- `test_live_mode_uses_live_provider_not_gamestate()`
- `test_replay_mode_uses_gamestate_not_live_provider()`
- `test_deprecation_warning_when_gamestate_used_in_live_mode()`

---

### Phase 5: Review & Complete Remaining UI Refactoring

**From git history, these UI refactoring tasks are in progress:**

1. ✅ **Commit 3039f0b**: "Remove legacy recording system" - DONE
2. ✅ **Commit 41649f3**: "UI revision audit" - DONE
3. ✅ **Phase 12D**: Capture stats panel, live balance display - DONE
4. ⏳ **This PR**: Socket deprecation cleanup - IN PROGRESS

**Remaining Work:**
- [ ] Phase 12E: Protocol Explorer UI (planned, not started)
- [ ] Integration tests for live/replay mode switching
- [ ] Documentation updates (CLAUDE.md, MIGRATION_GUIDE.md)

---

## Validation & Testing Strategy

### Unit Tests (New)
- Button state control (4 tests)
- Toast notification events (3 tests)
- Balance validation sources (2 tests)
- Live vs replay mode switching (3 tests)

### Integration Tests (New)
- Full live mode flow with LiveStateProvider
- Full replay mode flow with GameState only
- Mode switching (live → replay → live)
- Socket event → UI update chain

### Manual Testing Checklist
- [ ] Connect to live WebSocket, verify buttons enable/disable correctly
- [ ] Place trade, verify toast shows on TRADE_CONFIRMED
- [ ] Try to trade with insufficient balance, verify button disabled
- [ ] Switch to replay mode, verify GameState used instead
- [ ] Verify no deprecation warnings in live mode logs

---

## Migration Sequence (Recommended Order)

**Week 1:**
1. Phase 1: Button state control (2 days)
2. Phase 2: Toast consolidation (2 days)
3. Testing & bug fixes (1 day)

**Week 2:**
4. Phase 3: Balance validation (1 day)
5. Phase 4: GameState deprecation (2 days)
6. Phase 5: Complete remaining UI work (2 days)

**Week 3:**
7. Integration testing (2 days)
8. Documentation updates (1 day)
9. PR review & merge (2 days)

---

## Files to Modify Summary

### New Files
- `src/ui/handlers/button_state_handler.py` - Button state update logic
- `tests/ui/test_button_states.py` - Button state tests
- `tests/ui/test_toast_notifications.py` - Toast event tests

### Modified Files
- `src/ui/builders/action_builder.py` - Add state update method
- `src/ui/main_window.py` - Wire LiveStateProvider to buttons & toasts
- `src/ui/handlers/player_handlers.py` - Update buttons on PLAYER_UPDATE
- `src/ui/controllers/trading_controller.py` - Use LiveStateProvider for validation
- `src/ui/widgets/toast_notification.py` - Add socket event subscriptions
- `src/core/game_state.py` - Add deprecation warnings

### Files to Delete

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking replay mode | High | Add comprehensive replay mode tests first |
| Button state race conditions | Medium | Use TkDispatcher for all UI updates |
| Toast event spam | Low | Add debouncing/rate limiting |
| GameState removal breaks tests | Medium | Update tests incrementally, feature flags |

---

## Success Criteria

✅ **Complete when:**
1. All buttons use LiveStateProvider for enable/disable logic
2. Single toast notification system, wired to WebSocket events
3. No local balance validation in live mode (uses LiveStateProvider)
4. GameState only used in replay mode, LiveStateProvider in live mode
5. All tests pass (unit + integration)
6. No deprecation warnings in live mode logs
7. Manual testing checklist complete

---

## Questions for User

Before starting implementation:

1. **Button State Logic:** Should SIDEBET button check for existing active sidebet server-side, or trust the button state from `playerUpdate`?

2. **Toast Events:** Which socket events should trigger toasts? (See Phase 2 list - add/remove any?)

3. **GameState Migration:** Should we add a feature flag (`FORCE_LIVE_PROVIDER=true`) to enforce LiveStateProvider-only in live mode during migration?

4. **Timeline:** Is the 3-week timeline acceptable, or do you need faster completion?

5. **Scope:** Should we combine this with Phase 12E (Protocol Explorer UI), or keep them separate?

---

**Next Steps:** Review this plan, answer questions above, then begin Phase 1 implementation.
