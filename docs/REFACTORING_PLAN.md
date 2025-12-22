# VECTRA-PLAYER Refactoring Plan

**Status:** In Progress
**Created:** December 17, 2025
**Updated:** December 21, 2025
**Goal:** Clean-slate refactor maintaining exact behavior while eliminating technical debt

## Completed Phases

| Phase | Status | Date | Notes |
|-------|--------|------|-------|
| 0.1 Test Baseline | ✅ DONE | Dec 17 | 983 tests passing |
| 1.1 Fix Hardcoded Paths | ✅ DONE | Dec 17 | 11 paths fixed |
| 1.2 Fix Test Infrastructure | ✅ DONE | Dec 17 | sys.path.insert removed |
| 2.1 Remove Commented-Out Code | ✅ DONE | Dec 18 | Dead code removed |
| 3A Dual-Write to EventStore | ✅ DONE | Dec 18 | EventStoreService started in MainWindow |
| 3.2 Migration Path | ✅ DONE | Dec 18 | RUGS_LEGACY_RECORDERS env var added |
| 3.3 Cross-Repo Coordination | ✅ DONE | Dec 18 | docs/CROSS_REPO_COORDINATION.md created |
| 4.1 Phase Marker Cleanup | ✅ DONE | Dec 19 | 135→3 semantic only (automated review) |

---

## Executive Summary

VECTRA-PLAYER has accumulated significant technical debt from iterative development. This plan provides a systematic approach to clean up the codebase while **preserving all existing behavior**. The strategy follows TDD principles: characterize first, then refactor with confidence.

### Key Findings (Updated Dec 18)

| Category | Original | Current | Severity |
|----------|----------|---------|----------|
| Hardcoded `/home/nomad/` paths | 11 | **0** ✅ | **FIXED** |
| `sys.path.insert` anti-patterns | 3 | **0** ✅ | **FIXED** |
| Commented-out code blocks | 7 files | **2** ✅ | LOW |
| Phase markers (incomplete refactors) | 135 | **3** ✅ | **FIXED** (3 semantic only) |
| AUDIT FIX/PRODUCTION FIX patches | 183 | 183 | MEDIUM |
| Legacy/deprecated code | 4 instances | 4 | MEDIUM |
| **EventStore dual-write** | Not active | **Active** ✅ | **DONE** |

---

## Phase 0: Foundation (Days 1-2)

### 0.1 Establish Test Baseline

Before any changes, ensure all tests pass.

```bash
cd /home/user/VECTRA-PLAYER
pip install -e ".[dev]"
cd src && python -m pytest tests/ -v --tb=short
```

**Acceptance criteria:**
- [ ] All existing tests pass
- [ ] Coverage report generated as baseline
- [ ] Document any failing tests with root causes

### 0.2 Create Characterization Test Suite

Add tests that capture **current behavior** (even if quirky). These serve as golden masters for refactoring.

**Key areas needing characterization:**
1. **EventBus behavior** - The 8 "AUDIT FIX" patches indicate complex edge cases
2. **LiveFeedController** - 7 "PRODUCTION FIX" patches for race conditions
3. **GameState** - Duplicate stat tracking, deadlock prevention
4. **Recording system** - 3 different recorder implementations

**File locations:**
```
src/tests/test_characterization/
├── test_event_bus_behavior.py      # Capture all patched edge cases
├── test_live_feed_behavior.py      # Race condition scenarios
├── test_game_state_behavior.py     # Thread safety edge cases
└── test_recorder_behavior.py       # All 3 recorder outputs
```

---

## Phase 1: Critical Blockers (Days 3-5)

### 1.1 Fix Hardcoded Paths

**Files requiring changes:**

| File | Line | Fix |
|------|------|-----|
| `src/scripts/automated_bot_test.py` | 13-14, 226 | Use `RUGS_DATA_DIR` env var |
| `src/scripts/debug_bot_session.py` | 13-14, 226 | Use `RUGS_DATA_DIR` env var |
| `src/scripts/playwright_debug_helper.py` | 12-13 | Update docstrings |
| `src/tests/test_debug/test_raw_capture_recorder.py` | 21 | Use config paths |
| `src/tests/test_models/test_all_event_schemas.py` | 16 | Remove sys.path hack |
| `src/tests/test_models/test_player_update.py` | 11 | Remove sys.path hack |
| `src/tests/test_models/test_game_state_update.py` | 12 | Remove sys.path hack |

**Implementation:**

```python
# BEFORE (hardcoded)
Path("/home/nomad/rugs_recordings")

# AFTER (config-driven)
from config import Config
Config.get_files_config()["recordings_dir"]

# Or use environment variable
import os
from pathlib import Path
Path(os.getenv("RUGS_DATA_DIR", str(Path.home() / "rugs_data")))
```

**Test verification:**
```bash
# Should find zero hardcoded paths after fix
grep -r "/home/nomad" src/ --include="*.py" | grep -v "test_" | wc -l
# Expected: 0
```

### 1.2 Fix Test Infrastructure

Remove `sys.path.insert` anti-pattern from test files:

```python
# BEFORE
sys.path.insert(0, "/home/nomad/Desktop/VECTRA-PLAYER/src")

# AFTER (remove entirely - pytest handles this via pytest.ini)
# Just ensure pytest.ini has correct pythonpath:
# [pytest]
# pythonpath = .
```

**Verify pytest.ini configuration:**
```ini
[pytest]
pythonpath = .
testpaths = tests
```

---

## Phase 2: Dead Code Removal (Days 6-8)

### 2.1 Remove Commented-Out Code

**Files with substantial commented blocks:**

1. `src/ui/controllers/live_feed_controller.py` (lines 201-209)
   - Disabled auto-start recording code
   - **Action:** Delete if no longer needed, or create feature flag

2. `src/ui/main_window.py` (lines 158, 706, 1289)
   - **Action:** Audit each block, delete if unused

3. `src/browser/executor.py` (lines 45-53)
   - Legacy RugsBrowserManager fallback
   - **Action:** Remove after verifying CDP_MANAGER is stable

4. `src/core/validators.py`
   - **Action:** Audit and clean

5. `src/bot/strategies/base.py`
   - **Action:** Audit and clean

**Process for each file:**
1. Read the commented code
2. Search for any references to the commented functionality
3. If no references found, delete entirely
4. If references exist, decide: delete reference OR uncomment code
5. Run tests after each deletion

### 2.2 Remove Legacy Browser Fallback

`src/browser/executor.py` has deprecated code:

```python
# Current state (dual manager pattern)
CDP_MANAGER = "cdp"
LEGACY_MANAGER = "legacy"

# Target state (CDP only)
# Remove all LEGACY_MANAGER references
# Remove RugsBrowserManager import and fallback
```

**Verification:**
- All browser tests pass with CDP-only implementation
- No runtime fallback to legacy manager

---

## Phase 3: Consolidate Recording Systems (Days 9-12)

### 3.0 Key Finding: Public WebSocket Feed is Sufficient for ML

**Source:** `rugs-expert` agent analysis (December 18, 2025)

The public WebSocket feed (`gameStateUpdate`) contains **303+ fields** but we only capture 9.
This is sufficient for ML training without CDP/authenticated capture.

#### Data Available from Public Feed (Unauthenticated)

| Data | Fields | ML Relevance |
|------|--------|--------------|
| `gameStateUpdate` | 303+ fields | **HIGH** - Primary training data |
| `leaderboard[]` | All players' positions, PnL | **HIGH** - Market state |
| `gameHistory[]` | ~10 recent games with full price arrays | **HIGH** - Historical patterns |
| `partialPrices` | Backfill for missed ticks | MEDIUM - Gap filling |
| `statistics` | Session averages, highs | MEDIUM - Context |
| `rugpool` | Instarug risk metrics | LOW - Edge cases |

#### Data Requiring CDP/Auth

| Data | Purpose | ML Relevance |
|------|---------|--------------|
| `playerUpdate` | YOUR balance/position (server truth) | MEDIUM - Verification only |
| `gameStatePlayerUpdate` | Rugpool lottery details | LOW - Not core trading |
| Trade responses | Latency metrics | LOW - Execution analysis |

#### Recommendation: Simplified Architecture

```
Primary: Public WebSocket Feed (unauthenticated)
├── gameStateUpdate (P0) → 90% of ML training data
├── leaderboard[] → Market state (whale tracking!)
├── gameHistory[] → Historical patterns
└── partialPrices → Backfill missed ticks

Storage: EventStore → Parquet (canonical truth)

Optional: CDP Capture (authenticated)
├── playerUpdate → Server-authoritative verification
└── gameStatePlayerUpdate → Rugpool analytics
```

**Critical Gap:** We capture only 9 of 303+ fields in `gameStateUpdate`!
See GitHub Issue #31 for expanding capture + Live Feed Inspector window.

---

### 3.1 Current Recording Implementations

| Recorder | File | Purpose | Output | Keep? |
|----------|------|---------|--------|-------|
| RawCaptureRecorder | `src/debug/raw_capture_recorder.py` | Debug captures | JSONL | **Deprecate** → EventStore |
| DemoRecorderSink | `src/core/demo_recorder.py` | Human demonstrations | JSON per game | **Deprecate** → EventStore |
| UnifiedRecorder | `src/services/unified_recorder.py` | Main recording | Various | **Deprecate** → EventStore |
| **EventStore** | `src/services/event_store/` | Canonical truth | Parquet | **KEEP** (Phase 12) |

### 3.2 Migration Path

1. **Phase A**: Dual-write (EventStore + legacy recorders)
2. **Phase B**: Validate Parquet output matches legacy
3. **Phase C**: Disable legacy recorders via `RUGS_LEGACY_RECORDERS=false`
4. **Phase D**: Delete legacy recorder code

### 3.3 Cross-Repo Coordination

Recording consolidation requires coordination with:
- **claude-flow**: `rugs-expert` agent will query EventStore data via ChromaDB
- **rugs-rl-bot**: ML training consumes Parquet exports from EventStore

See `docs/CROSS_REPO_COORDINATION.md` for integration points.

---

## Phase 4: Clean Up Phase Markers (Days 13-15)

### 4.1 Inventory Phase Comments

125 phase markers across 31 files indicate incomplete refactoring waves:

**Phases found:** 1, 2, 3.2-3.5, 4, 5, 6, 7, 8.1-8.6, 9.1, 9.3, 10, 10.2-10.8, 11, 12

### 4.2 Convert to Documentation

For each phase marker:

1. **If the phase is complete:** Remove the comment
2. **If the phase is incomplete:** Create a TODO issue in GitHub
3. **If the comment explains WHY:** Convert to docstring

**Example transformation:**
```python
# BEFORE
# Phase 10.6: Auto-start recording DISABLED
# Recording is now controlled via UI toggle, not auto-started

# AFTER (if keeping explanation)
"""
Note: Auto-recording is controlled via UI toggle, not started automatically.
This was changed to give users explicit control over when recording begins.
"""
```

### 4.3 Clean Up AUDIT FIX Comments

183 "AUDIT FIX" and "PRODUCTION FIX" comments indicate reactive patches.

**Process:**
1. For each AUDIT FIX, add a proper test that exercises the edge case
2. Once test exists, simplify the comment to just reference the test
3. If the fix is well-tested, remove the verbose comment

```python
# BEFORE
# AUDIT FIX: Prevent deadlock when subscriber callback raises
# This was added after production incident where...
# [10 lines of explanation]

# AFTER
# See test_event_bus_behavior.py::test_subscriber_exception_no_deadlock
```

---

## Phase 5: Naming and Structure Consistency (Days 16-18)

### 5.1 Module Organization Audit

Current structure is generally good. Minor improvements:

```
src/
├── bot/              # OK
├── browser/          # OK
├── core/             # OK
├── debug/            # Consider: merge into services/debug/
├── ml/               # OK
├── models/           # OK - split events/ is clean
├── scripts/          # Consider: move to top-level scripts/
├── services/         # OK
├── sources/          # OK
├── tests/            # OK
├── ui/               # OK - builders/controllers pattern is clean
└── utils/            # OK
```

### 5.2 Naming Consistency

**Issues found:**
- Mixed private/public method naming in controllers
- Inconsistent event naming between EventBus and WebSocket handlers

**Recommendation:** Document conventions, don't mass-rename (too risky for behavior parity)

### 5.3 Refactor main_window.py Monolith ⭐ NEW

**Priority:** HIGH
**Risk Level:** HIGH
**Status:** Not Started

#### Problem Statement

`src/ui/main_window.py` has grown to **1866 lines** with multiple concerns mixed together:

| Section | Lines | Responsibility |
|---------|-------|----------------|
| Initialization | 52-173 | Component setup (browser, bot, recorders, event store) |
| Menu Creation | 175-256 | MenuBarBuilder configuration (80 lines of callbacks) |
| **UI Construction** | 258-651 | **390 lines** of widget creation |
| Event Handlers Setup | 653-683 | Event bus subscriptions |
| Replay Callbacks | 695-844 | Tick updates, game end logic |
| Event Handlers | 846-1006 | 15+ handler methods |
| Balance Lock/Unlock | 1008-1140 | Balance editing UI (130 lines) |
| Keyboard Shortcuts | 1142-1248 | Setup + help dialog |
| Theme Management | 1250-1421 | Theme switching, preferences, restart |
| Demo Recording | 1456-1532 | Session/game handlers |
| Unified Recording | 1533-1623 | Recording config, status |
| Raw Capture | 1624-1810 | Developer tools |
| Shutdown | 1811-1866 | Cleanup orchestration |

#### Proposed Structure

```
src/ui/
├── main_window.py              # Slim orchestrator (~200 lines)
│
├── window/                      # Window lifecycle & construction
│   ├── __init__.py
│   ├── initialization.py       # Component init (browser, bot, recorders)
│   ├── ui_builder.py          # UI widget construction (split from _create_ui)
│   ├── menu_setup.py          # Menu bar callback wiring
│   └── shutdown.py            # Cleanup orchestration
│
├── handlers/                    # Event & callback handlers
│   ├── __init__.py
│   ├── replay_handlers.py     # _on_tick_update, _process_tick_ui, _on_game_end
│   ├── event_handlers.py      # Game tick, trades, file loaded
│   ├── player_handlers.py     # Player identity, updates, server state
│   ├── balance_handlers.py    # Balance lock/unlock/edit dialogs
│   ├── recording_handlers.py  # Demo + unified recording methods
│   └── capture_handlers.py    # Raw capture developer tools
│
├── interactions/                # User interactions
│   ├── __init__.py
│   ├── keyboard_shortcuts.py  # Shortcut setup + help dialog
│   └── theme_manager.py       # Theme switching, preferences, restart
│
└── controllers/                 # (Already exists - no changes)
    ├── bot_manager.py
    ├── replay_controller.py
    └── ...
```

#### Implementation Steps

**Step 1: Create Module Structure** (0.5 days)
```bash
mkdir -p src/ui/window src/ui/handlers src/ui/interactions
touch src/ui/window/__init__.py
touch src/ui/handlers/__init__.py
touch src/ui/interactions/__init__.py
```

**Step 2: Extract Handlers** (1 day)

Priority order (least risky → most risky):
1. `keyboard_shortcuts.py` - Self-contained, easy to test
2. `theme_manager.py` - Self-contained, static methods
3. `capture_handlers.py` - Developer tools, isolated
4. `recording_handlers.py` - Clear boundaries
5. `balance_handlers.py` - Dialog logic
6. `player_handlers.py` - Server state
7. `event_handlers.py` - Core event handling
8. `replay_handlers.py` - Tick processing (most critical)

**Step 3: Extract Window Modules** (1 day)
1. `shutdown.py` - Cleanup logic
2. `initialization.py` - Component init
3. `menu_setup.py` - Menu callbacks
4. `ui_builder.py` - Widget construction (largest)

**Step 4: Refactor main_window.py** (0.5 days)
- Import extracted modules
- Delegate to extracted methods
- Keep public API identical: `from ui.main_window import MainWindow`

**Step 5: Test Each Extraction** (1 day)
```bash
# After EACH module extraction:
cd src && python -m pytest tests/ -v --tb=short -k "test_main_window or test_ui"

# Integration test
./run.sh  # Launch app, verify all features work
```

#### Acceptance Criteria

- [ ] All tests pass after refactoring
- [ ] `from ui.main_window import MainWindow` still works (backwards compatible)
- [ ] main_window.py reduced from 1866 → ~200 lines
- [ ] Each new module is 100-250 lines (readable size)
- [ ] No behavior changes (UI, keyboard shortcuts, recording all work)
- [ ] Each module has clear single responsibility

#### Risk Mitigation

**High-Risk Areas:**
1. **Replay tick processing** - Critical path, high throughput
   - Mitigation: Extract LAST, test heavily
2. **Event handler wiring** - Easy to break subscriptions
   - Mitigation: Keep handler setup in one place, verify subscriptions
3. **Circular imports** - MainWindow imports handlers, handlers import MainWindow
   - Mitigation: Use TYPE_CHECKING, pass dependencies explicitly

**Rollback Strategy:**
- Each extraction is a separate commit
- If tests fail, revert that commit and investigate
- Don't extract multiple modules in one commit

#### Testing Strategy

1. **Unit tests**: Test each extracted module independently
2. **Integration tests**: Launch app, click through all UI features
3. **Regression tests**: Run full test suite after each extraction

```bash
# Comprehensive verification
cd src

# 1. Unit tests
python -m pytest tests/test_ui/ -v

# 2. Full suite
python -m pytest tests/ -v --tb=short

# 3. Manual smoke test
cd .. && ./run.sh
# - Test keyboard shortcuts (Space, B, S, D, L, H)
# - Test menu items (File, View, Settings, Dev)
# - Test live feed toggle
# - Test recording toggle
# - Test theme switching
```

#### Dependencies

- **Prerequisite:** Phase 4.1 (Phase marker cleanup) ✅ DONE
- **Prerequisite:** Phase 2.1 (Commented code removal) ✅ DONE
- **Enables:** Easier testing, better maintainability for all future UI work

#### Estimated Effort

- Module creation: 0.5 days
- Handler extraction: 1 day
- Window module extraction: 1 day
- Main window refactor: 0.5 days
- Testing & verification: 1 day
- **Total: 4 days** (included in Phase 5 duration)

---

---

## Phase 6: Strategy Pattern Cleanup (Days 19-20)

### 6.1 Bot Strategy Duplication

Current strategies have similar boilerplate:
- `foundational.py` (9,623 bytes) - largest
- `aggressive.py` (2,812 bytes)
- `conservative.py` (2,210 bytes)
- `sidebet.py` (2,339 bytes)

**Analysis needed:**
1. Extract common decision logic to base class
2. Keep strategy-specific parameters configurable
3. Ensure behavior parity with characterization tests

---

## Phase 7: Final Verification (Days 21-22)

### 7.1 Regression Testing

```bash
# Full test suite
cd src && python -m pytest tests/ -v --tb=short

# Coverage comparison
python -m pytest tests/ --cov=. --cov-report=html
# Compare to Phase 0 baseline
```

### 7.2 Behavior Verification

- [ ] Live feed connects and receives data
- [ ] Replay playback works for all game types
- [ ] Bot strategies execute correctly
- [ ] Recording produces valid output
- [ ] UI displays correctly

### 7.3 Static Analysis

```bash
# No hardcoded paths
grep -r "/home/nomad" src/ --include="*.py" | wc -l  # Should be 0

# No sys.path hacks in tests
grep -r "sys.path.insert" src/tests/ | wc -l  # Should be 0

# Ruff passes
ruff check src/
```

---

## Execution Order Summary

| Phase | Focus | Duration | Risk |
|-------|-------|----------|------|
| 0 | Test baseline & characterization | 2 days | Low |
| 1 | Fix critical blockers (paths) | 3 days | Medium |
| 2 | Remove dead code | 3 days | Medium |
| 3 | Consolidate recorders | 4 days | High |
| 4 | Clean phase markers | 3 days | Low |
| 5 | Naming/structure **+ main_window.py refactor** | **5 days** | **High** |
| 6 | Strategy cleanup | 2 days | Medium |
| 7 | Final verification | 2 days | Low |

**Total:** ~24 days of focused work

**Phase 5 Breakdown:**
- 5.1 Module organization audit: 0.5 days
- 5.2 Naming consistency: 0.5 days
- **5.3 main_window.py refactor: 4 days** ⭐ NEW

---

## Success Criteria

1. **Zero hardcoded paths** - All paths use config/environment
2. **All tests pass** - Including new characterization tests
3. **No commented-out code** - Clean diffs, clear history
4. **Phase comments removed** - Or converted to proper docs
5. **AUDIT FIX comments minimized** - Covered by tests instead
6. **main_window.py modularized** - Reduced from 1866 → ~200 lines ⭐ NEW
7. **Identical behavior** - UI, recording, playback work exactly as before

---

## Risk Mitigation

### High-Risk Changes

1. **EventBus modifications** - Core pub/sub system
   - Mitigation: Extensive characterization tests first

2. **Recorder consolidation** - Data could be lost
   - Mitigation: Keep all recorders, just document/organize

3. **Browser executor cleanup** - Could break automation
   - Mitigation: Test with real browser sessions

### Rollback Strategy

Each phase should be a separate commit (or PR). If issues found:
1. Revert the phase commit
2. Add failing test for the issue
3. Re-apply with fix

---

## Files to Delete (Candidates)

After characterization testing, these are deletion candidates:

| File | Reason | Verify First |
|------|--------|--------------|
| `sandbox/explore_websocket_data.py` | Development tool, not production | Check if used |
| Legacy imports in `browser/executor.py` | Deprecated fallback | Test CDP-only |

---

## Appendix: Technical Debt Inventory

### A.1 Complete Hardcoded Path List

```
src/scripts/automated_bot_test.py:13  - docstring
src/scripts/automated_bot_test.py:14  - docstring
src/scripts/debug_bot_session.py:13   - docstring
src/scripts/debug_bot_session.py:14   - docstring
src/scripts/debug_bot_session.py:226  - runtime Path()
src/scripts/playwright_debug_helper.py:12 - docstring
src/scripts/playwright_debug_helper.py:13 - docstring
src/tests/test_debug/test_raw_capture_recorder.py:21 - assertion
src/tests/test_models/test_all_event_schemas.py:16   - sys.path
src/tests/test_models/test_player_update.py:11       - sys.path
src/tests/test_models/test_game_state_update.py:12   - sys.path
```

### A.2 Phase Marker Distribution

| File | Phase Count |
|------|-------------|
| `ui/main_window.py` | 15+ |
| `ui/controllers/live_feed_controller.py` | 10+ |
| `core/replay_engine.py` | 8+ |
| `services/event_bus.py` | Heavy |

### A.3 Files with Most Technical Debt

1. **`src/ui/main_window.py`** - **1866 lines** (monolithic, to be refactored in Phase 5.3) ⭐ NEW
2. `src/services/event_bus.py` - 8 AUDIT FIX patches
3. `src/ui/controllers/live_feed_controller.py` - 7 PRODUCTION FIX patches
4. `src/core/game_state.py` - Multiple patches
5. `src/browser/executor.py` - Legacy fallback code

### A.4 main_window.py Detailed Breakdown ⭐ NEW

**Total Lines:** 1866
**Primary Issues:** God object anti-pattern, mixed concerns, difficult to test

| Concern | Lines | Extract To |
|---------|-------|------------|
| Initialization | 121 | `window/initialization.py` |
| Menu callbacks | 82 | `window/menu_setup.py` |
| UI construction | 393 | `window/ui_builder.py` |
| Replay callbacks | 150 | `handlers/replay_handlers.py` |
| Event handlers | 161 | `handlers/event_handlers.py` |
| Player/server state | 128 | `handlers/player_handlers.py` |
| Balance lock/unlock | 133 | `handlers/balance_handlers.py` |
| Keyboard shortcuts | 107 | `interactions/keyboard_shortcuts.py` |
| Theme management | 172 | `interactions/theme_manager.py` |
| Recording handlers | 168 | `handlers/recording_handlers.py` |
| Raw capture tools | 187 | `handlers/capture_handlers.py` |
| Shutdown | 56 | `window/shutdown.py` |

**Post-refactor:** ~200 lines (orchestration + delegation only)

---

*This plan should be executed incrementally with frequent commits. Each phase builds on the previous one's stability.*
