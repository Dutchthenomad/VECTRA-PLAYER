# Comprehensive Codebase Audit Summary

**Date:** 2025-12-22
**Reviewer:** Meta-audit of agent-generated reports
**Scope:** All `/src` subdirectories

---

## Audit Reports Inventory

| Location | Report File | Lines | Focus Area |
|----------|-------------|-------|------------|
| `src/` | `SRC_CODEBASE_AUDIT.md` | 122 | Entry points (config.py, main.py) |
| `src/browser/` | `BROWSER_CODEBASE_AUDIT.md` | 166 | CDP/Playwright automation |
| `src/core/` | `CORE_CODEBASE_AUDIT.md` | 208 | Game state, replay engine |
| `src/debug/` | `DEBUG_CODE_AUDIT.md` | 111 | Debug tooling |
| `src/ml/` | `ML_CODE_AUDIT.md` | 164 | Sidebet predictor, training |
| `src/models/` | `MODELS_CODE_AUDIT.md` | 169 | Dataclasses, Pydantic schemas |
| `src/services/` | `SERVICES_CODE_AUDIT.md` | 240 | EventBus, EventStore |
| `src/sources/` | `SOURCES_CODE_AUDIT.md` | 167 | WebSocket feed, CDP interceptor |
| `src/ui/` | `UI_CODEBASE_AUDIT.md` | 188 | Controllers, handlers, widgets |
| `src/utils/` | `UTILS_CODE_AUDIT.md` | 121 | Decimal utilities |

**Additional Context Files:**
- `src/models/events/CONTEXT.md` - Event schema documentation
- `src/services/event_store/CONTEXT.md` - EventStore architecture

---

## Critical Findings Summary (P0 - Fix Immediately)

### 1. Runtime Crashes / Guaranteed Exceptions

| Issue | Location | Impact |
|-------|----------|--------|
| `isinstance(v, int \| float)` is invalid Python | `models/events/game_state_update.py:202` | Schema validation crashes |
| `TradeManager` treats sidebet dict as object | `core/trade_manager.py:296+` | `AttributeError` on rug/expiry check |
| `BotManager.toggle_bot()` assumes `current_tick` is object | `ui/controllers/bot_manager.py:116` | `AttributeError` on bot disable |
| `BotManager.show_bot_config()` uses invalid kwargs | `ui/controllers/bot_manager.py:176` | `TypeError: bootstyle` |
| `LiveFeedController` calls nonexistent `set_seed_data()` | `ui/controllers/live_feed_controller.py:238` | `AttributeError` |
| `BrowserConnectionDialog` constructor signature wrong | `ui/controllers/browser_bridge_controller.py:73` | `TypeError` on dialog open |

### 2. Import-Time Crashes

| Issue | Location | Impact |
|-------|----------|--------|
| Invalid `CDP_PORT` env crashes at import | `config.py` | App fails before logging |
| `duckdb` not optional - breaks UI tests | `ui/main_window.py:24` | Test collection fails |
| ML stack imports at module level | `ml/__init__.py` | Fails without sklearn |

### 3. Windows Portability

| Issue | Location | Impact |
|-------|----------|--------|
| `signal.SIGALRM` is Unix-only | `main.py:shutdown()` | `AttributeError` on Windows |

---

## High Priority Findings (P1 - Fix Soon)

### Thread Safety / Concurrency

1. **BrowserConnectionDialog** - Tkinter operations from background thread (`ui/browser_connection_dialog.py:150-223`)
2. **PlaybackController** - Can spawn duplicate playback threads; `cleanup()` can deadlock by joining own thread (`core/replay_playback_controller.py`)
3. **LiveFeedController tick coalescing** - Drops ticks under load, corrupting recordings (`ui/controllers/live_feed_controller.py:67-123`)
4. **EventSourceManager** - Publishes events while holding lock (`services/event_source_manager.py`)
5. **CDPBrowserManager** - stderr PIPE not drained, can block Chrome (`browser/manager.py`)

### Data Integrity

1. **Double game finalization** - `PriceHistoryHandler` emits "game complete" twice (`sources/price_history_handler.py`)
2. **Filename path traversal** - Unsanitized `username` in filenames (legacy recorders)
3. **SQL injection risk** - String interpolation in DuckDB queries (`services/event_store/duckdb.py`)
4. **Unreachable duplicate code** - Dead code in `socketio_parser.py` after `return`
5. **CDP connection state** - `is_connected` not updated on WebSocket close (`sources/cdp_websocket_interceptor.py`)

### API/Contract Mismatches

1. **Event publishing shape wrong** - `WS_RAW_EVENT` double-wrapped (`browser/bridge.py`)
2. **Timeout exception type wrong** - Catches built-in `TimeoutError` not Playwright's (`browser/automation.py:124`)
3. **Latency calculations inverted** - `client_timestamp - self.timestamp` likely negative (`models/events/trade_events.py`)
4. **`GameState.get_current_tick()`** - Reports `rug_detected` as `rugged` (wrong field) (`core/game_state.py:175`)

---

## Medium Priority Findings (P2)

### Configuration/Serialization

- Config `save_to_file()` omits `files` section but `load_from_file()` supports it
- JSON round-trip doesn't preserve `frozenset` types
- Timestamp timezone inconsistency (naive vs UTC-aware) across codebase

### Code Quality

- Multiple `sys.path` injections at runtime (`main.py`, `browser/bridge.py`, `vector_indexer/indexer.py`)
- Mixed `print()` vs `logging` in browser/ML modules
- Duplicate selector definitions (`browser/dom/selectors.py` vs `browser/bridge.py`)
- `service.py.backup` checked into source tree

### Behavioral Gaps

- Backtester enforces 50-tick spacing, not documented 45
- ML training crashes on single-class datasets

---

## Gaps Identified (Not Covered by Agent Reports)

### 1. Test Coverage Gaps

The agents noted tests pass but several high-priority bugs exist because:
- Core tests don't exercise `TradeManager.check_and_handle_rug()`
- UI tests skip in headless environments (91 skipped)
- No integration tests for live feed → core → recording path

### 2. Cross-Module Integration Issues

Several bugs span multiple modules (e.g., UI calls core method that assumes wrong type). The individual audits identified these but a dedicated integration audit would help:
- `UI → Core → Services` tick flow
- `Browser → EventBus → UI` event shape
- `Config → All modules` env var handling

### 3. Scripts Directory Not Audited

The `/src/scripts/` directory was not covered by any agent report:
- `query_session.py`
- `export_jsonl.py`
- `convert_captured_to_parquet.py`
- `validate_eventstore_e2e.py`
- `analyze_raw_capture.py`

### 4. Bot Strategies Not Audited

`/src/bot/` only has strategies marked deprecated, but `bot/controller.py` wasn't explicitly reviewed.

### 5. Browser Automation Submodule

`/src/browser_automation/` exists but wasn't mentioned in any report.

---

## Prioritized Fix Order

### Wave 1: Stop the Crashes (1-2 days)
1. Fix `isinstance(v, int | float)` → `isinstance(v, (int, float))`
2. Fix `TradeManager` sidebet dict vs object
3. Fix UI controller crashes (5 issues)
4. Make `CDP_PORT` parsing safe
5. Guard Windows `signal.SIGALRM`

### Wave 2: Thread Safety (2-3 days)
1. Fix `BrowserConnectionDialog` Tkinter threading
2. Fix `PlaybackController` lifecycle (duplicate threads, deadlock)
3. Review live feed tick coalescing - decide if drops are acceptable
4. Release locks before event publishing

### Wave 3: Data Integrity (1-2 days)
1. Fix double game finalization in `PriceHistoryHandler`
2. Sanitize filenames in legacy outputs (if any remain)
3. Use parameterized queries in DuckDB
4. Remove unreachable code in `socketio_parser.py`

### Wave 4: API Contracts (1-2 days)
1. Fix `WS_RAW_EVENT` publishing shape
2. Fix Playwright timeout exception handling
3. Fix latency calculation sign
4. Fix `GameState.get_current_tick()` rugged field

---

## Validation Checklist (Post-Fix)

```bash
# Full test suite
cd /home/nomad/Desktop/VECTRA-PLAYER/src
../.venv/bin/python -m pytest tests/ -v --tb=short

# Static analysis
../.venv/bin/ruff check .
../.venv/bin/mypy core/ bot/ services/ --ignore-missing-imports

# Syntax check all modules
find . -name "*.py" -exec python3 -m py_compile {} \;

# Manual smoke test
cd .. && ./run.sh
# - Toggle live feed on/off
# - Start/stop recording
# - Run bot briefly
# - Check no exceptions in terminal
```

---

## Appendix: File Counts by Directory

```
src/
├── bot/           4 files (strategies deprecated)
├── browser/       9 files + dom/ + cdp/
├── browser_automation/ (not audited)
├── core/         12 files
├── debug/         2 files
├── ml/            6 files
├── models/        9 files + events/
├── scripts/       5 files (not audited)
├── services/     12 files + event_store/ + schema_validator/ + vector_indexer/
├── sources/      10 files
├── ui/           15 files + builders/ + controllers/ + handlers/ + interactions/ + widgets/ + window/
└── utils/         2 files
```

---

*Generated: 2025-12-22 by meta-audit of 11 agent reports*
