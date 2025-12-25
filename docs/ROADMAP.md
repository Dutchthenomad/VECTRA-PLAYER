# Roadmap

Last updated: 2025-12-25

This roadmap unifies remaining goals and cleanup work. It is the canonical
reference for planning and execution.

## Phase 1: Remaining P0 Crash Fixes (Immediate) ✅ COMPLETE

All 12 P0 items fixed with AUDIT FIX comments. Verified 926 tests passing.

Scope (all fixed):
- Core: PlaybackController cleanup self-join deadlock. ✅
- Core: PlaybackController duplicate thread/zombie playback loop. ✅
- UI: BotManager uses tick.active instead of game_active. ✅
- UI: Toast bootstyle misuse. ✅
- UI: LiveFeedController calls nonexistent set_seed_data(). ✅
- UI: BrowserConnectionDialog constructor missing required arg. ✅
- UI: RecordingController calls missing toast.show(). ✅ (removed)
- Browser: WS_RAW_EVENT double-wrapped publish. ✅
- Browser: Playwright timeout exception type mismatch. ✅
- Browser: Runtime sys.path mutation in BrowserBridge. ✅
- Sources: socketio_parser unreachable duplicate code. ✅
- Sources: PriceHistoryHandler double-finalization. ✅

Acceptance checks:
- Repro steps for each crash no longer throw. ✅
- `cd src && pytest tests/ -v` passes (926 tests). ✅

## Phase 2: Thread-Safety and Data Integrity (Stabilization) ✅ COMPLETE

Scope:
- EventSourceManager publishes while holding lock.
- CDPBrowserManager stderr pipe can block Chrome.
- Live feed race conditions and state reconciliation gaps.

Completed (2025-12-24 via PR #142):
- Fixed event_source_manager.py lock contention
- Fixed browser/manager.py stderr pipe blocking
- Fixed live_feed_controller.py race conditions
- Fixed live_state_provider.py state reconciliation
- 926 tests passing

Acceptance checks:
- No Tk thread violations under live feed stress. ✅
- Long-running automation sessions do not stall due to blocked pipes. ✅

## Phase 3: GUI Audit Remediation (Phase 12E Prep)

Scope:
- Move UI subprocess work off the UI thread.
- Remove legacy recorder mixins and menu items.
- Standardize EventBus -> EventStore capture path.

Acceptance checks:
- UI remains responsive during capture analysis.
- No legacy recorder codepaths reachable in live mode.

Execution note:
- This phase must be completed by a different model (not this agent).

## Phase 4: Socket Cleanup and Live/Replay Separation

Scope:
- Button state control based on LiveStateProvider.
- Live validation uses server balance when connected.
- GameState becomes replay-only; live mode read-only or unused.

Acceptance checks:
- Live mode buttons reflect server state correctly.
- No GameState mutation in live mode without warning.

## Phase 5: Quality Sweep

Scope:
- Resolve remaining P2/P3 audit items.
- Add tests for fixed crash paths and regressions.

Acceptance checks:
- `ruff check .` clean.
- Coverage does not regress.

## Phase 6: BotActionInterface Implementation ✅ COMPLETE

**Completed:** 2025-12-25 | **Tests:** 166 new, 1092 total passing

**Design Doc:** `docs/plans/2025-12-23-bot-action-interface-design.md`

Implementation summary:

| Phase | Component | Tests |
|-------|-----------|-------|
| 1 | `types.py` - ActionParams, ActionResult, ExecutionMode, GameContext | 20 |
| 2 | `executors/base.py` + `simulated.py` - ABC and SimulatedExecutor | 21 |
| 3 | `executors/tkinter.py` - TkinterExecutor wrapping BotUIController | 21 |
| 4 | `confirmation/monitor.py` + `mock.py` - ConfirmationMonitor | 21 |
| 5 | `state/tracker.py` - HYBRID StateTracker | 12 |
| 6 | `interface.py` - BotActionInterface orchestrator | 17 |
| 7 | `factory.py` - Factory functions for all 4 modes | 17 |
| 8 | `recording/human_interceptor.py` - HumanActionInterceptor | 37 |

Architecture ("Player Piano"):
```
RECORDING   → Human plays, system records inputs with full context
TRAINING    → RL model trains with fast SimulatedExecutor
VALIDATION  → Model replays pre-recorded games with UI animation
LIVE        → Real browser automation (v1.0 stub, v2.0 PuppeteerExecutor)
```

**Note:** This phase covers BUY, SELL, SIDEBET only. Shorting deferred (see below).

Acceptance checks:
- Bot can execute trades via all three modes ✅
- Confirmation latency tracked and exposed ✅
- Factory functions for TRAINING/RECORDING/VALIDATION/LIVE modes ✅

## Phase 7: Shorting Integration ⛔ DEFERRED

**Status:** DEFERRED until empirical protocol data captured

**Reason (2025-12-24):** rugs-expert agent confirmed no WebSocket event captures
exist for shorting. All mechanics are unknown:
- No `shortOrder` request/response events documented
- `shortPosition` field always `null` in all captures
- UI buttons and XPaths unknown
- Leverage and liquidation mechanics undocumented

**Prerequisites before implementation:**
1. Live CDP capture of player opening/closing short position
2. Document WebSocket request/response format
3. Understand UI buttons and flow via browser inspection
4. Validate mechanics (leverage, liquidation, amounts)

**Research Location:** claude-flow rugs-expert agent

## Phase 8: Button XPath Verification & Automation (Non-Short Buttons)

**Design Doc:** `docs/plans/2025-12-24-shorting-integration-and-button-automation.md`

Scope:
- Verify button XPaths via CDP for documented features
- Document automation approach (button click vs HTTP POST)
- Implement Playwright button click methods
- Add CDP health check and reconnection

Button inventory (v1.0 - excluding shorts):
- Trade: BUY, SELL (10%/25%/50%/100%)
- Sidebets: SIDEBET
- Bet amounts: X (clear), +0.001, +0.01, +0.1, +1, 1/2, X2, MAX
- Controls: Wallet connect, refresh, settings

**Deferred buttons:** SHORT_OPEN, SHORT_CLOSE, SHORT percentages (pending Phase 7)

Acceptance checks:
- All documented buttons have verified XPaths
- Playwright can click each button type
- Automation mode selection working

## Cleanup Track (Continuous)

- Archive superseded status/audit/plan docs to
  `sandbox/DEVELOPMENT DEPRECATIONS/`.
- Avoid new ad-hoc summary docs; update this roadmap instead.
- When deprecating a doc, add a short note indicating the archive location.

---

## Design Documents Reference

| Phase | Document |
|-------|----------|
| Phase 6 | `docs/plans/2025-12-23-bot-action-interface-design.md` |
| Phase 7-8 | `docs/plans/2025-12-24-shorting-integration-and-button-automation.md` |
| rugs-expert | `claude-flow/knowledge/rugs-strategy/L2-protocol/confirmation-mapping.md` |
| Schema v2.0 | `docs/plans/2025-12-23-expanded-event-schema-design.md` |
