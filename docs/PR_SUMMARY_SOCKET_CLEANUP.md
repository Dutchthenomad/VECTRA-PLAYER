# PR Summary: Socket Deprecation & UI Refactoring Cleanup

**Branch:** `claude/cleanup-deprecated-socket-logic-PDwKv`
**Type:** Planning / Documentation
**Phase:** 12D - System Validation & Legacy Consolidation
**Status:** Planning Complete - Ready for Implementation Session

---

## Overview

This PR documents the comprehensive cleanup plan for deprecated systems following the successful Phase 12C LiveStateProvider integration. Now that server-authoritative state is available via WebSockets, several legacy local-state systems need to be deprecated or removed.

**No code changes in this PR** - this is a planning document to be used in a dedicated implementation session.

---

## What This PR Contains

### Documentation Added

1. **`docs/plans/socket-deprecation-cleanup-plan.md`** (365 lines)
   - Comprehensive 5-phase migration strategy
   - Detailed file-by-file analysis of deprecated systems
   - Testing strategy and success criteria
   - 3-week implementation timeline
   - Risk assessment and mitigation
   - Questions for clarification before implementation

---

## Background: Phase 12C Success

Phase 12C successfully implemented LiveStateProvider, which provides server-authoritative state from WebSocket `playerUpdate` events:

✅ **Working Systems:**
- LiveStateProvider receives real-time player updates
- Balance display uses server state when connected
- State reconciliation detects and logs drift
- EventStore captures all events to Parquet
- Thread-safe state access throughout

**Source:** `src/services/live_state_provider.py` (372 lines, 20 tests passing)

---

## Problems Identified

### 1. Button State Control: MISSING

**Current State:** All action buttons (SIDEBET, BUY, SELL) are hardcoded to `state=tk.NORMAL`

**Location:** `src/ui/builders/action_builder.py:89, 100, 111`

```python
# Current: Always enabled
sidebet_button = tk.Button(..., state=tk.NORMAL)
buy_button = tk.Button(..., state=tk.NORMAL)
sell_button = tk.Button(..., state=tk.NORMAL)
```

**Problem:**
- Users can click buttons even when server would reject (insufficient balance, no position, game inactive)
- Browser receives click BEFORE validation happens (lines 120-126 in `trading_controller.py`)
- No visual feedback about button availability

**Impact:** Poor UX, potential confusion when trades fail after button click

**Required Fix:** Wire LiveStateProvider to dynamically enable/disable buttons:
- SIDEBET: Check `live_provider.cash >= min_bet` and game active
- BUY: Check `live_provider.cash >= min_bet` and game active
- SELL: Check `live_provider.has_position`
- All: Disabled when `!live_provider.is_connected`

---

### 2. Local Balance Validation: DEPRECATED

**Current State:** TradingController validates against local GameState balance

**Location:** `src/ui/controllers/trading_controller.py:363, 390-392`

```python
# Line 363 - MAX button
balance = self.state.get("balance")

# Line 390-392 - Bet validation
balance = self.state.get("balance")
if bet_amount > balance:
    self.toast.show(f"Insufficient balance! Have {balance:.4f} SOL", "error")
    return None
```

**Problem:**
- Local balance can drift from server truth
- Validation happens AFTER browser click is sent
- Not using server-authoritative `LiveStateProvider.cash`

**Required Fix:**
```python
# Check mode and use appropriate source
if hasattr(self.parent, 'live_state_provider') and self.parent.live_state_provider.is_connected:
    balance = self.parent.live_state_provider.cash
else:
    balance = self.state.get("balance")  # Fallback for replay mode
```

---

### 4. GameState for Live Mode: DEPRECATED

**Current State:** GameState used for both live and replay modes

**Location:** `src/core/game_state.py` (990 lines)

**Current Responsibilities:**
- Local state tracking (balance, position, sidebet, tick)
- Trade execution state (P&L calculations, position management)
- Observer pattern for state changes
- **Phase 11 addition:** `reconcile_with_server()` method to sync with server

**Problem:**
- Dual state system: GameState (local) + LiveStateProvider (server)
- Reconciliation overhead on every `playerUpdate` event
- Confusion about which is "source of truth"
- GameState still updated in live mode (should be read-only)

**Correct Architecture:**
- **Live Mode:** LiveStateProvider is sole source of truth, GameState read-only or unused
- **Replay Mode:** GameState is source of truth, LiveStateProvider unavailable

**Required Fix:**
- Add mode-aware helpers: `get_current_balance()`, `get_current_position()`
- Add deprecation warnings when GameState mutated in live mode
- Update UI components to check mode before choosing state source
- Make GameState replay-only in future phases

---

## Proposed Solution: 5-Phase Migration

### Phase 1: Implement Button State Control (2 days)

**Goal:** Add dynamic button enable/disable using LiveStateProvider

**Changes:**
- Add `update_button_states()` method to ActionBuilder
- Subscribe to `PLAYER_UPDATE`, `GAME_TICK`, `WS_SOURCE_CHANGED` events
- Update buttons on every state change
- Use TkDispatcher for thread-safe UI updates

**Tests:** 4 new unit tests for button state logic

---

### Phase 2: Replace Local Balance Validation (1 day)

**Goal:** Use LiveStateProvider for all validation in live mode

**Changes:**
- Update `trading_controller.py:363, 390-392`
- Add mode detection: live mode → LiveStateProvider, replay mode → GameState
- Same pattern for MAX button, bet validation

**Tests:** 2 new tests for mode-aware validation

---

### Phase 3: Deprecate GameState for Live Mode (2 days)

**Goal:** Make GameState replay-only, LiveStateProvider for live

**Changes:**
- Add mode-aware helpers: `get_current_balance()`, `get_current_position()`
- Add deprecation warnings when GameState mutated in live mode
- Update TradeManager, balance handlers, UI components
- Document new patterns in MIGRATION_GUIDE.md

**Tests:** 3 new tests for mode switching and deprecation warnings

---

### Phase 4: Complete UI Refactoring (2 days)

**Goal:** Finish remaining work, integration tests, docs

**Changes:**
- Integration tests for live/replay mode switching
- Update CLAUDE.md with new patterns
- Update MIGRATION_GUIDE.md with examples
- Manual testing checklist
- PR review prep

---

## Timeline

**Week 1:** Phases 1-2 (Button states + Toast consolidation)
**Week 2:** Phases 3-4 (Balance validation + GameState deprecation)
**Week 3:** Phase 4 (Integration testing + docs)

**Total:** ~3 weeks for full implementation

---

## Files Summary

### New Files
- ✅ `docs/plans/socket-deprecation-cleanup-plan.md` (this PR)
- 📅 `src/ui/handlers/button_state_handler.py` (future)
- 📅 `tests/ui/test_button_states.py` (future)
- 📅 `tests/ui/test_toast_notifications.py` (future)

### Modified Files (Future PRs)
- `src/ui/builders/action_builder.py`
- `src/ui/main_window.py`
- `src/ui/handlers/player_handlers.py`
- `src/ui/controllers/trading_controller.py`
- `src/ui/widgets/toast_notification.py`
- `src/core/game_state.py`

---

## Related Work

### Completed
- ✅ Phase 12A: Event schemas (58 tests)
- ✅ Phase 12B: Parquet Writer + EventStore (84 tests)
- ✅ Phase 12C: LiveStateProvider (20 tests)
- ✅ Commit 3039f0b: Legacy recording system removal
- ✅ Commit 41649f3: UI audit complete

### In Progress
- ⏳ Phase 12D: System validation & legacy consolidation (this plan)

### Planned
- 📅 Phase 12E: Protocol Explorer UI
- 📅 Full ChromaDB vector indexing
- 📅 RAG-powered event search

---

## Success Criteria

This planning phase is complete when:
- ✅ Comprehensive cleanup plan documented
- ✅ All deprecated systems identified and analyzed
- ✅ Migration strategy defined with timelines
- ✅ Files to modify/delete mapped out
- ✅ Testing strategy defined
- ✅ PR created for review

**For future implementation PRs:**
1. All buttons use LiveStateProvider for enable/disable logic
2. Single toast notification system, wired to WebSocket events
3. No local balance validation in live mode
4. GameState only used in replay mode
5. All tests pass (unit + integration)
6. No deprecation warnings in live mode logs

---

## Questions for Implementation Session

Before starting implementation, clarify:

1. **Button Logic:** Should SIDEBET check for active sidebets server-side, or trust playerUpdate state?

2. **Toast Events:** Which socket events should trigger toasts?
   - Suggested: TRADE_CONFIRMED, TRADE_REJECTED, INSUFFICIENT_BALANCE, SIDEBET_PLACED, SIDEBET_RESOLVED, RUG_DETECTED, GAME_STARTED, GAME_ENDED
   - Add/remove any?

3. **Feature Flag:** Add `FORCE_LIVE_PROVIDER=true` env var to enforce LiveStateProvider-only during migration?

4. **Timeline:** 3-week timeline acceptable, or need faster/slower?

5. **Scope:** Combine with Phase 12E (Protocol Explorer UI), or keep separate PRs?

6. **Testing:** Should we add property-based tests for state reconciliation edge cases?

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking replay mode | High | Add comprehensive replay mode tests first, feature flags |
| Button state race conditions | Medium | Use TkDispatcher for all UI updates, add locks where needed |
| Toast event spam | Low | Add debouncing/rate limiting to toast manager |
| GameState removal breaks tests | Medium | Update tests incrementally, use deprecation warnings first |
| State drift during migration | Medium | Keep reconciliation active, add monitoring/alerts |

---

## Next Steps

1. **Review this plan** in dedicated planning session
2. **Answer clarification questions** above
3. **Create implementation PR** from this branch
4. **Begin Phase 1** (Button State Control)
5. **Iterate** through phases 2-5

---

## References

- **Main Plan:** `docs/plans/socket-deprecation-cleanup-plan.md`
- **Phase 12 Design:** `sandbox/2025-12-15-phase-12-unified-data-architecture-design.md`
- **Migration Guide:** `docs/MIGRATION_GUIDE.md`
- **WebSocket Spec:** `docs/specs/WEBSOCKET_EVENTS_SPEC.md`
- **LiveStateProvider:** `src/services/live_state_provider.py`
- **CLAUDE.md:** Root-level project documentation

---

**Ready for dedicated planning session.** No code changes in this PR - documentation only.
