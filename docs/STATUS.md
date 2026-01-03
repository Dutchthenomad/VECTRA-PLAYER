# Project Status

Last updated: 2026-01-03

## Canonical Status Sources

- This file is the source of truth for current status.
- The active roadmap is in `docs/ROADMAP.md`.
- Superseded status/audit/plan documents are archived in
  `sandbox/DEVELOPMENT DEPRECATIONS/`.

## Current Phase

**Phase 6: BotActionInterface** - ✅ COMPLETE (2025-12-25)

All 8 implementation phases done. 166 new tests, 1092 total tests passing.

## Critical Decision: Shorting Deferred (2025-12-24)

rugs-expert agent confirmed **no empirical data exists** for shorting:
- `shortPosition` always `null` in all WebSocket captures
- No `shortOrder` events documented
- UI buttons and mechanics unknown

**Action:** Shorting removed from v1.0 scope. Research continues in claude-flow.

## Completed

- ✅ Phase 12A-12D: EventStore, schemas, LiveStateProvider
- ✅ Schema v2.0.0: Expanded event types (PR #141)
- ✅ Phase 1: All 12 P0 crash fixes (AUDIT FIX comments verified)
- ✅ Phase 2: Thread-safety stabilization (PR #142)
- ✅ rugs-expert integration: ChromaDB ingestion, confirmation mapping
- ✅ Design docs: BotActionInterface, button XPaths
- ✅ XPaths verified production-ready (no audit needed)
- ✅ Phase 6: BotActionInterface (166 tests, "Player Piano" architecture)

## Phase 6 Implementation Summary

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

**Architecture ("Player Piano"):**
```
RECORDING   → Human plays, system records inputs with full context
TRAINING    → RL model trains with fast SimulatedExecutor
VALIDATION  → Model replays pre-recorded games with UI animation
LIVE        → Real browser automation (v1.0 stub, v2.0 PuppeteerExecutor)
```

## Now (Highest Priority)

**✅ Migration Stabilization Complete (Jan 3, 2026)**

Priority 1 tasks completed:
- ✅ Issues #138-140: Closed Dec 26, 2025
- ✅ MinimalWindow implementation complete
- ✅ Test suite: 1138/1138 passing (100%)
- ✅ Async cleanup improvements committed
- ✅ Path verification: 34 RUGS_DATA_DIR refs, 2 legacy for replay compat
- ✅ System ready for production development

**Next Steps:**
- Pipeline D: RL training data generation
- CDP connection stability verification
- Phase 3-5 roadmap execution

## Deferred (Pending Research)

- Phase 7: Shorting integration (requires live protocol capture first)

## Recent Accomplishments

| Date | Event | Description |
|------|-------|-------------|
| 2026-01-03 | Priority 1 | Migration stabilization complete - system stable |
| 2026-01-03 | f6bdc9d | Async cleanup improvements in tests |
| 2026-01-02 | 1355dfc | Chrome `rugs_bot` profile configured as default |
| 2026-01-01 | dc3d1a2 | WIP: Migration from old development machine |
| 2025-12-28 | Milestone | MinimalWindow implementation complete |
| 2025-12-26 | Issues | #138-140 closed (toast, paths, legacy cleanup) |
| 2025-12-25 | Phase 6 | BotActionInterface COMPLETE - 166 tests |
| 2025-12-24 | Decision | Shorting deferred - no empirical data |

## Design Documents

| Document | Purpose | Status |
|----------|---------|--------|
| `docs/plans/2025-12-23-bot-action-interface-design.md` | BotActionInterface | ✅ Implemented |
| `docs/plans/2025-12-24-shorting-integration-and-button-automation.md` | Button XPaths | Partial (shorting deferred) |
| `claude-flow/.../confirmation-mapping.md` | Action→Event mapping | Ready |

## Archive Policy

If a status, audit, plan, or summary doc is replaced by this file or
`docs/ROADMAP.md`, it should be moved to
`sandbox/DEVELOPMENT DEPRECATIONS/` rather than deleted.
