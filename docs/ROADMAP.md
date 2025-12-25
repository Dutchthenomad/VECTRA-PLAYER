# Roadmap

Last updated: 2025-12-24

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

## Phase 6: BotActionInterface Implementation

**Design Doc:** `docs/plans/2025-12-23-bot-action-interface-design.md`

Scope (Track A from rugs-expert analysis):
- Day 1-2: ActionExecutor layer (Tkinter/Puppeteer/Simulated modes)
- Day 3-4: ConfirmationMonitor (WebSocket subscription, latency tracking)
- Day 5-6: StateTracker (wraps LiveStateProvider)
- Day 7-9: Integration, testing, and BotController migration

Architecture:
```
BotActionInterface
├── ActionExecutor (execution modes: SIMULATED, UI_LAYER, BROWSER)
├── ConfirmationMonitor (playerUpdate/currentSidebet subscriptions)
└── StateTracker (server-authoritative state wrapper)
```

Acceptance checks:
- Bot can execute trades via all three modes
- Confirmation latency tracked and exposed
- BotController uses new interface exclusively

## Phase 7: Shorting Integration

**Design Doc:** `docs/plans/2025-12-24-shorting-integration-and-button-automation.md`

Scope:
- Add SHORT_OPEN/SHORT_CLOSE to ActionType enum (already in schema)
- Implement shorting logic in ActionExecutor
- Add short position display to UI
- Integrate with LiveStateProvider short position tracking

Acceptance checks:
- Bot can open/close short positions
- Short P&L calculated correctly
- UI displays short position status

## Phase 8: Button XPath Verification & Automation

**Design Doc:** `docs/plans/2025-12-24-shorting-integration-and-button-automation.md`

Scope:
- Verify all 24 button XPaths via CDP
- Document automation approach (button click vs HTTP POST)
- Implement Playwright button click methods
- Add CDP health check and reconnection

Button inventory (24 total):
- Trade: BUY, SELL_25/50/75/100, SHORT_OPEN, SHORT_CLOSE
- Sidebets: SIDEBET_UP/DOWN, BBC_BULL/BEAR/CRAB, CANDLE_FLIP
- Bet amounts: 6 preset buttons
- Controls: Wallet connect, refresh, settings

Acceptance checks:
- All buttons have verified XPaths
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
