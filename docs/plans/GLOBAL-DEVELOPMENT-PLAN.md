# VECTRA-PLAYER Global Development Plan

**Date:** 2026-01-17 (Updated - Foundation Service + Artifact Framework)
**Status:** CANONICAL - Master Plan (supersedes ALL individual phase docs)
**Purpose:** Unified, gated development roadmap integrating foundation audit + bot training pipeline
**Tests:** 1138+ passing

---

## ⚠️ AUTHORITATIVE DOCUMENT NOTICE

**This is THE single source of truth for VECTRA-PLAYER development.**

Individual phase documents are kept for historical reference only. If there's a conflict between this document and any other, THIS DOCUMENT WINS.

### Document Hierarchy

| Document | Status | Purpose |
|----------|--------|---------|
| **GLOBAL-DEVELOPMENT-PLAN.md** | **CANONICAL** | Master plan - follow this |
| `.claude/scratchpad.md` | Session State | Session-level context |
| `sandbox/DEVELOPMENT DEPRECATIONS/*` | Archived | Historical reference only |

**Reference Docs Moved:** All individual phase docs have been moved to `sandbox/DEVELOPMENT DEPRECATIONS/` (2025-12-27).

### Governing Standard

This plan follows the **Development Documentation and Gating Standard** defined in:
`/home/nomad/Desktop/claude-flow/docs/plans/DEVELOPMENT-DOCUMENTATION-AND-GATING-STANDARD.md`

Key principles:
- Gates require verification evidence before claiming complete
- No work added without plan update
- Session scratchpad is ephemeral, not authoritative

### Ownership Split

| Repository | Owns | Does NOT Own |
|------------|------|--------------|
| **VECTRA-PLAYER** | Implementation, development plans, codebase docs | Protocol knowledge, agent configs |
| **claude-flow** | WebSocket protocol spec, RAG knowledge base, expert agents, workflow commands | Code implementation |

---

## Executive Summary

Two parallel planning efforts have been created:
1. **First Principles Codebase Audit** - Fix foundation before adding features
2. **Bot Training Pipeline** - Feature development for RL training data capture

This document merges them into a single, properly-gated plan where foundation work enables feature development.

---

## Critical Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FOUNDATION LAYER                                     │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ Audit Ph 1-2 │───►│ Audit Ph 3   │───►│ Audit Ph 4-5 │                  │
│  │ Data Flow +  │    │ SSOT         │    │ Test Infra + │                  │
│  │ Contracts    │    │ Assignment   │    │ Foundation   │                  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                  │                          │
│                                                  ▼                          │
│  ═══════════════════════════════════════════════════════════════════════   │
│                          FOUNDATION GATE                                    │
│            (Event contracts documented, SSOT defined, tests real)           │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                  │                          │
└──────────────────────────────────────────────────┼──────────────────────────┘
                                                   │
┌──────────────────────────────────────────────────┼──────────────────────────┐
│                         FEATURE LAYER            │                          │
│                                                  ▼                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │ Pipeline A   │───►│ Pipeline B   │───►│ Pipeline C   │───►│Pipeline D│ │
│  │ Server State │    │ ButtonEvent  │    │ Action       │    │Training  │ │
│  │ Validation   │    │ Capture      │    │ Validation   │    │Pipeline  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Status Overview

| Phase | Name | Status | Blocker |
|-------|------|--------|---------|
| **FOUNDATION** | | | |
| Audit 1 | Data Flow Mapping | 🔄 PARTIAL | None - Event structure documented during Bug 7 fix |
| Audit 2 | Contract Verification | 🔄 PARTIAL | Bug 7 fix validated event contracts |
| Audit 3 | Responsibility Clarification | ⏳ PENDING | Need SSOT decision for balance/position |
| Audit 4 | Test Infrastructure | ⏳ PENDING | Audit 3 |
| Audit 5 | Foundation Fixes | 🔄 PARTIAL | Bug 7 fix applied |
| **UI MIGRATION** | | | |
| MinimalWindow | UI Simplification | ✅ COMPLETE (2025-12-28) | None - Wiring fixes applied |
| **FEATURES** | | | |
| Pipeline A | Server State Validation | ✅ VERIFIED | None |
| Pipeline B | ButtonEvent Implementation | ✅ VERIFIED (2025-12-27) | None - Gate passed |
| Pipeline C | Player Action Validation | ✅ COMPLETE (2025-12-28) | None - Gate passed |
| Pipeline D | Training Pipeline | ⏳ **READY TO START** | None - All prerequisites met |
| **POLISH** | | | |
| Audit 6 | Gated Development Validation | ⏳ PENDING | Pipeline D |
| Audit 7 | UI Redesign Prep | ⏳ PENDING | Audit 6 |
| **INFRASTRUCTURE** | | | |
| Foundation | WebSocket Broadcaster + HTTP Monitor | ✅ COMPLETE (2026-01-17) | None |
| Artifacts | HTML Tool Framework | ✅ COMPLETE (2026-01-17) | Foundation |

**Legend:** ✅ Complete | 🔄 Partial | ⚠️ Ready for verification | ⏳ Pending/Blocked

### MinimalWindow Migration (2025-12-28) ✅ COMPLETE

**What Was Done:**
- Replaced 8-mixin MainWindow (8,700 LOC) with MinimalWindow (850 LOC)
- 93% UI code reduction
- CONNECT button for CDP connection
- Server-authoritative design (no local validation blocking)
- 30 legacy UI files archived to `src/ui/_archived/`

**Wiring Fixes Applied (Same Session):**
- C1: `browser_bridge` passed to MinimalWindow in `main.py`
- H2: `LiveStateProvider` created in `main.py`
- H3: `EventStoreService` started in `main.py`
- H5: `BrowserBridge.on_status_change` callback wired in `minimal_window.py`

**Verification:** CDP connects, buttons emit events, 1565 events captured to Parquet

### Foundation Service (2026-01-17) ✅ COMPLETE

**What Was Done:**
- Added Foundation Service from `feature/typescript-frontend-api` branch
- WebSocket broadcaster on port 9000 for HTML tools
- Monitoring HTTP server on port 9001
- Event normalization (rugs.fun → unified event types)

**Files Added:**
```
src/foundation/
├── __init__.py
├── config.py           # FoundationConfig with env vars
├── connection.py       # ConnectionState machine
├── normalizer.py       # Event normalization
├── broadcaster.py      # WebSocket server (port 9000)
├── service.py          # FoundationService orchestrator
├── http_server.py      # Monitoring UI (port 9001)
├── runner.py           # CLI runner
└── launcher.py         # Full startup with Chrome/CDP
```

**Event Types (Normalized):**
| Event Type | Source Event | Purpose |
|------------|--------------|---------|
| `game.tick` | `gameStateUpdate` | Price/tick updates |
| `player.state` | `playerUpdate` | Balance, position |
| `connection.authenticated` | `usernameStatus` | Auth status |
| `player.trade` | `standard/newTrade` | Trade events |
| `sidebet.placed` | `currentSidebet` | Sidebet events |

### HTML Artifact Framework (2026-01-17) ✅ COMPLETE

**What Was Done:**
- Created modular HTML tool framework
- Shared infrastructure (WebSocket client, styles, templates)
- Two tools: Seed Bruteforce + Prediction Engine
- Tab-based Orchestrator wrapper

**Directory Structure:**
```
src/artifacts/
├── shared/
│   ├── foundation-ws-client.js   # WebSocket client
│   └── vectra-styles.css         # Catppuccin theme
├── templates/
│   ├── artifact-template.html    # Base template
│   └── artifact-template.js      # JS skeleton
├── tools/
│   ├── seed-bruteforce/          # PRNG seed analysis
│   └── prediction-engine/        # Bayesian price predictor
│       └── components/
│           ├── equilibrium-tracker.js
│           ├── dynamic-weighter.js
│           ├── stochastic-oscillator.js
│           └── bayesian-forecaster.js
└── orchestrator/                 # Tab wrapper
    ├── index.html
    ├── orchestrator.js
    └── registry.json
```

**Verification:** All files created, committed to main branch

---

## Completed Work (Reference)

### Bug Hunt Resolutions (2025-12-27)

| # | Bug | Root Cause | Fix | Impact |
|---|-----|------------|-----|--------|
| 1 | CDP→Fallback drop | Socket.IO not found in window.* | Dynamic Socket.IO discovery + don't stop CDP on failure | CDP stays running |
| 2 | rugs_websocket_id None | WebSocket created before CDP attached | CDP waits for natural reconnection | WebSocket captured |
| 3 | Stale log message | .pyc bytecode cache | Cleared __pycache__ directories | Clean logs |
| 4 | Fallback not live | Naming mismatch (FALLBACK vs public_ws) | Renamed FALLBACK → PUBLIC_WS | is_live works |
| 5 | tickCount extraction | Wrong field name (tick vs tickCount) | Fixed to use tickCount | Tick data flows |
| 6 | Session stats location | Expected nested sessionStats | Fixed to extract from top level | Stats work |
| 7 | **game_active never set** | **Event extraction looked in wrong place** | **Fixed `_on_ws_raw_event` to check `wrapped.get("event")` instead of `data.get("event")`** | **Trading enabled** |

**Bug 7 Details:** The event structure from CDPWebSocketInterceptor puts `event` at the top level, but `GameState._on_ws_raw_event` was looking for it inside the `data` dict. Fixed in `src/core/game_state.py:914`.

**Verification:** 1138 tests pass (2025-12-27)

### Pipeline Phase A (Complete)

18+ server state fields validated against WebSocket protocol spec:
- tick, price, game_phase, cooldown_timer_ms
- balance, position_qty, avg_entry_price
- rugpool_amount, rugpool_threshold
- average_multiplier, count_2x/10x/50x/100x
- highest_today, connected_players

---

## Current Priority: Pipeline D - Training Data Pipeline

### Phase B: ButtonEvent Implementation ✅ VERIFIED

**Status:** ✅ VERIFIED (2025-12-27) - Gate passed with evidence

**Completed:**
- [x] ButtonEvent dataclass in `src/models/events/button_event.py`
- [x] ActionSequence dataclass
- [x] BUTTON_PRESS event in EventBus
- [x] BUTTON_EVENT doc_type in EventStore
- [x] TradingController emits ButtonEvents
- [x] EventStoreService subscribes to BUTTON_PRESS
- [x] LiveStateProvider extracts tick/price/game_id from gameStateUpdate
- [x] Bug 7 Fix: GameState._on_ws_raw_event correctly extracts event name
- [x] **Gate Verification: ButtonEvents capture real game context**

**Gate Verification Evidence (2025-12-27):**
```
Pipeline B Gate Verification:
  tick = 712 (requirement: > 0) ✅
  price = 3.6935944603476845 (requirement: != 1.0) ✅
  game_id = 20251227-cc7643caf6624686 (requirement: != "unknown") ✅

Sample ButtonEvents captured:
  SELL tick=712 price=3.69 game_id=20251227-cc7643caf6624686
  SIDEBET tick=697 price=4.75 game_id=20251227-cc7643caf6624686
  BUY tick=685 price=5.22 game_id=20251227-cc7643caf6624686
```

---

## Upcoming Phases

### Phase C: Player Action Feature Validation ✅ COMPLETE (2025-12-28)

**Prerequisite:** Phase B gate passed ✅

**Deliverables:**
1. [x] Validate ButtonEvent fields against recordings
2. [x] Validate action timing features (ticks_since_last_action) - Range 1-517 ✅
3. [x] Validate sequence grouping logic - Unique sequence_id per action ✅
4. [x] Update observation-space-design.md with action features
5. [x] Implement time_in_position tracking in LiveStateProvider (6 tests)
6. [x] Finalize observation space schema (36 validated, 7 pending)

**Implementation Evidence (2025-12-28):**
- `time_in_position`: Implemented in LiveStateProvider with 6 TDD tests
  - Tracks `entry_tick` when positionQty changes from 0 → non-zero
  - Calculates `time_in_position = current_tick - entry_tick`
  - Resets on: game_id change, position close (qty → 0)
- Execution tracking fields added to ButtonEvent:
  - `execution_tick`, `execution_price`, `trade_id`
  - `client_timestamp`, `latency_ms`, `time_in_position`
- Validated by rugs-expert agent against WebSocket protocol spec

**Validation Evidence (2025-12-27):**
- `ticks_since_last_action`: 20/20 valid int values, range 1-517
- `bet_amount`: 17/20 nonzero (3 with 0.0 are SELL actions as expected)
- Action sequences: Properly grouped with unique sequence_id

**Gate:** ✅ PASSED - All player action features validated and implemented (1149 tests passing)

### Phase D: Training Pipeline ⏳ READY TO START

**Prerequisite:** Phase C gate passed ✅ (2025-12-28)

**Deliverables:**
1. [ ] Implement training data export from Parquet
2. [ ] Create observation vector builder (36 validated features)
3. [ ] Implement episode boundary detection (game_id changes)
4. [ ] Create training dataset generator
5. [ ] Validate with RL environment integration

**Gate:** Can generate valid training batches from recorded data

---

## Foundation Audit Integration

The audit phases run IN PARALLEL with feature development, but inform and unblock it.

### Audit Phase 1-2: Data Flow + Contracts

**When:** Can run now, independent of feature work

**Deliverables:**
- Data source/sink inventory
- Real event samples captured
- Field mapping table (expected vs actual)

**Scripts ready:**
- `scripts/capture_event_structures.py`
- `scripts/diagnose_game_state_events.py`

### Audit Phase 3: SSOT Assignment

**When:** After Phase 1-2

**Key Decision:** Who owns what data in live vs replay mode?

| Data | Replay SSOT | Live SSOT | Current |
|------|-------------|-----------|---------|
| tick | ReplayEngine | LiveStateProvider | ✅ Fixed |
| price | ReplayEngine | LiveStateProvider | ✅ Fixed |
| game_active | ReplayEngine | GameState (synced from WS) | ✅ Fixed |
| balance | GameState | LiveStateProvider | ⚠️ Dual |
| position | GameState | LiveStateProvider | ⚠️ Dual |

### Audit Phase 4-5: Test Infra + Foundation Fixes

**When:** After Phase 3

**Key Work:**
- Replace mocked tests with real event fixtures
- Standardize event format throughout codebase
- Eliminate silent failures and default value masking

---

## Gating Rules (MANDATORY)

### Rule 1: Gate on Any Valid Data Source
- ❌ BAD: "Requires CDP specifically"
- ✅ GOOD: "Requires ANY live source (CDP OR PUBLIC_WS)"

### Rule 2: Verify Before Claiming Complete
- ❌ BAD: "Code is written, phase complete"
- ✅ GOOD: "Ran verification, output shows real data"

### Rule 3: Don't Skip Foundation for Features
- ❌ BAD: "Just add the feature, we'll fix data flow later"
- ✅ GOOD: "Data flow works → Feature works → Gate passed"

### Rule 4: Tests Must Use Real Data
- ❌ BAD: Tests pass with mocked events that don't match production
- ✅ GOOD: Tests use fixtures captured from real WebSocket

---

## Quick Reference: What To Do Next

### Completed This Session (2025-12-28)

**MinimalWindow Migration + Wiring Fixes:**
- ✅ MinimalWindow replaces MainWindow (93% code reduction)
- ✅ CDP connection working (1565 events captured)
- ✅ ButtonEvents emit on BUY/SELL/SIDEBET clicks
- ✅ All 1138 tests passing
- ✅ Pushed to GitHub (commit 340798a)

### Current: Pipeline D - Training Data Pipeline

**Status:** READY TO START - All prerequisites met

**Objective:** Generate RL training data from captured gameplay sessions

**Implementation Plan:** `docs/plans/2025-12-28-pipeline-d-training-data-implementation.md`

**Tasks:**
1. [ ] Create Observation Schema (`src/ml/schemas.py`)
2. [ ] Create Episode Segmenter (`src/ml/episode_segmenter.py`)
3. [ ] Create Observation Builder (`src/ml/observation_builder.py`)
4. [ ] Create Training Generator (`src/ml/training_generator.py`)
5. [ ] Integration test with real Parquet data

**Observation Space (36 validated features):**
- 22 server state features (tick, price, balance, rugpool, etc.)
- 6 derived features (velocity, acceleration, PnL, etc.)
- 3 player action features (time_in_position, ticks_since_last_action, bet_amount)
- 5 execution tracking features (execution_tick, latency_ms, etc.)

**Reference:** `scripts/FLOW-CHARTS/observation-space-design.md`

**Gate Criteria:** Can generate valid training batches from recorded data

### Data Available for Training

```
Current Parquet inventory:
  ws_event:      31,744 events (game state, player updates)
  button_event:     204 events (human actions with full context)
  Distinct games:    59
```

---

## Document References

| Document | Purpose |
|----------|---------|
| `2026-01-17-consolidation-plan.md` | Foundation + Artifacts implementation plan |
| `2025-12-28-pipeline-d-training-data-implementation.md` | Training pipeline implementation |
| `2025-12-27-first-principles-codebase-audit.md` | Detailed audit phase specifications |
| `2025-12-26-revised-bot-training-pipeline.md` | Detailed pipeline phase specifications |
| `2025-12-27-cdp-websocket-bug-hunt.md` | Bug hunt history and resolutions |
| `observation-space-field-validation-report.md` | Phase A validation results |

---

## Success Criteria (End State)

When complete, VECTRA-PLAYER will have:

1. **Documented Data Flow:** Every event type traced from source to sink
2. **Real Test Fixtures:** Tests use captured production data
3. **Single Source of Truth:** Clear SSOT for each piece of state
4. **ButtonEvent Capture:** Human actions logged with full game context
5. **Training Pipeline:** Can generate RL training data from sessions
6. **No Silent Failures:** All errors surface immediately
