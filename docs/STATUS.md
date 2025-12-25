# Project Status

Last updated: 2025-12-25

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

**Project Chores (GitHub Issues):**
- #138: Migrate Toast to Socket Events
- #139: Path Migration to RUGS_DATA_DIR
- #140: Final Legacy Cleanup

**Documentation:**
- claude-flow #24: Ingest empirical validation data
- BotActionInterface docs for L4-vectra-codebase

## Deferred (Pending Research)

- Phase 7: Shorting integration (requires live protocol capture first)

## Recent Accomplishments

| Date | Event | Description |
|------|-------|-------------|
| 2025-12-25 | Phase 6 | BotActionInterface COMPLETE - 166 tests |
| 2025-12-24 | Decision | Shorting deferred - no empirical data |
| 2025-12-24 | PR #142 | Phase 2 Stabilization + Canonical Docs |
| 2025-12-24 | 3b5c7d5 | Fix missing _handle_game_tick handler |

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
