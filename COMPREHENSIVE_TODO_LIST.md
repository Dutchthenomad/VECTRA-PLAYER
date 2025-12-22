# Comprehensive Bug Fix TODO List
**Date:** December 22, 2025
**Branch:** `claude/audit-codebase-ui-revision-WUtDa`
**Status:** Cross-referenced my fixes with newly merged audit

---

## ✅ COMPLETED (My Fixes - 9 Categories)

### 1. ✅ Null Pointer Dereferences in Demo Recorder
- **File:** `src/ui/main_window.py`
- **Lines:** 1521-1616
- **Fixed:** Added null checks to 5 demo_recorder methods
- **Commit:** 5c72da0

### 2. ✅ Event Handler Cleanup
- **File:** `src/ui/main_window.py`
- **Lines:** 1930-1967
- **Fixed:** Unsubscribe 14 event handlers in shutdown()
- **Commit:** 5c72da0

### 3. ✅ Silent Decimal Conversion Failures
- **File:** `src/ui/controllers/trading_controller.py`
- **Lines:** 88-97, 272-279, 306-315, 325-334
- **Fixed:** Added InvalidOperation handling with logging
- **Commit:** 5c72da0

### 4. ✅ Undefined Names (TYPE_CHECKING)
- **Files:** `core/game_state.py`, `ui/browser_connection_dialog.py`, `ui/controllers/browser_bridge_controller.py`, `ui/controllers/live_feed_controller.py`
- **Fixed:** Added TYPE_CHECKING imports, fixed lambda closures
- **Commit:** 5be9f9e

### 5. ✅ JSON Parsing Failure Logging
- **File:** `src/sources/socketio_parser.py`
- **Lines:** 86-92, 153-159, 169-181
- **Fixed:** Added logging to 3 JSONDecodeError handlers
- **Commit:** 5be9f9e

### 6. ✅ Directory Creation Failure Logging
- **File:** `src/services/event_store/paths.py`
- **Lines:** 87-101
- **Fixed:** Specific exception handling (PermissionError, OSError)
- **Commit:** 5be9f9e

### 7. ✅ Whitespace Issues (W293)
- **Fixed:** 11 blank lines with trailing whitespace
- **Commit:** 5be9f9e

### 8. ✅ Service Initialization Validation
- **File:** `src/ui/main_window.py`
- **Lines:** 122-140
- **Fixed:** Wrapped EventStore and LiveStateProvider init in try/except
- **Commit:** df18612

### 9. ✅ Browser Bridge Resilience
- **File:** `src/ui/controllers/trading_controller.py`
- **Lines:** 9 methods wrapped with error handling
- **Fixed:** All browser_bridge calls wrapped to prevent crashes
- **Commit:** df18612

---

## 🔴 P0 - RUNTIME CRASHES (Must Fix Immediately - 21 Issues)

These will crash the application immediately when triggered.

### Models (1 issue)

#### P0-1: `isinstance(v, int | float)` TypeError
- **File:** `src/models/events/game_state_update.py`
- **Line:** 202
- **Issue:** `isinstance(x, int | float)` is invalid syntax, raises TypeError
- **Impact:** Crashes on validation of max_bet/max_win in AvailableShitcoin
- **Fix:** Replace with `isinstance(v, (int, float))`
- **Audit:** MODELS_CODE_AUDIT.md

### Core (4 issues)

#### P0-2: TradeManager sidebet type mismatch
- **File:** `src/core/trade_manager.py`
- **Lines:** 278-339 (check_and_handle_rug, check_sidebet_expiry)
- **Issue:** Code expects `sidebet.placed_tick` but GameState stores dict `{"placed_tick": ...}`
- **Impact:** AttributeError when rug occurs with active sidebet
- **Fix:** Access as dict: `sidebet["placed_tick"]`, `sidebet["amount"]`
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P0-3: GameState.get_current_tick() wrong field name
- **File:** `src/core/game_state.py`
- **Line:** 175
- **Issue:** Returns `GameTick(rugged=self._state.get("rug_detected"))` instead of `"rugged"`
- **Impact:** Tick.rugged always False even when game is rugged
- **Fix:** Change to `rugged=self._state.get("rugged", False)`
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P0-4: PlaybackController.cleanup() self-join deadlock
- **File:** `src/core/replay_playback_controller.py`
- **Lines:** 273-284
- **Issue:** cleanup() joins playback_thread without self-join guard
- **Impact:** Deadlock if cleanup() called from playback thread
- **Fix:** Add guard like pause() has (lines 94-101)
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P0-5: PlaybackController zombie threads
- **File:** `src/core/replay_playback_controller.py`
- **Lines:** 63-104, 238-268
- **Issue:** pause() doesn't set _stop_event, play() can start duplicate threads
- **Impact:** Double-stepping, race conditions
- **Fix:** Wake loop on pause, prevent duplicate thread starts
- **Audit:** CORE_CODEBASE_AUDIT.md

### UI (5 issues)

#### P0-6: BotManager.toggle_bot() AttributeError
- **File:** `src/ui/controllers/bot_manager.py`
- **Lines:** 116-120
- **Issue:** `current_tick = self.state.get("current_tick")` is int, code uses `current_tick.active`
- **Impact:** Crash when disabling bot during active game
- **Fix:** Get active state from GameState API, not tick.active
- **Audit:** UI_CODEBASE_AUDIT.md

#### P0-7: BotManager.show_bot_config() TypeError
- **File:** `src/ui/controllers/bot_manager.py`
- **Lines:** 176-181
- **Issue:** Calls `self.toast.show(..., bootstyle="success")` but ToastNotification doesn't accept bootstyle
- **Impact:** Crash on bot config update
- **Fix:** Remove `bootstyle` kwarg
- **Audit:** UI_CODEBASE_AUDIT.md

#### P0-8: LiveFeedController calls nonexistent set_seed_data()
- **File:** `src/ui/controllers/live_feed_controller.py`
- **Lines:** 232-239
- **Issue:** Calls `ReplayEngine.set_seed_data()` which doesn't exist
- **Impact:** Crash when gameComplete arrives with seedData
- **Fix:** Remove call or implement method in ReplayEngine
- **Audit:** UI_CODEBASE_AUDIT.md

#### P0-9: BrowserConnectionDialog wrong constructor signature
- **File:** `src/ui/controllers/browser_bridge_controller.py`
- **Lines:** 73-78
- **Issue:** BrowserConnectionDialog requires `browser_executor` arg, not provided
- **Impact:** Crash when opening legacy browser connection dialog
- **Fix:** Pass `browser_executor` or update dialog constructor
- **Audit:** UI_CODEBASE_AUDIT.md

#### P0-10: RecordingController calls nonexistent toast.show()
- **File:** `src/ui/controllers/recording_controller.py`
- **Lines:** 157-161
- **Issue:** Calls `self._toast.show()` but RecordingToastManager has `recording_started()` not `show()`
- **Impact:** Crash in EventStore-only mode (RUGS_LEGACY_RECORDERS=false)
- **Fix:** Call correct method: `self._toast.recording_started(...)`
- **Audit:** UI_CODEBASE_AUDIT.md

### Browser (3 issues)

#### P0-11: WS_RAW_EVENT double-wrapped (OVERLAPS WITH MY FIX?)
- **File:** `src/browser/bridge.py`
- **Issue:** Publishes `{"data": event}` instead of `event` directly
- **Impact:** DebugTerminal sees `{"data": {"data": event}}` and can't parse
- **Fix:** Publish `event` directly: `publish(Events.WS_RAW_EVENT, event)`
- **Audit:** BROWSER_CODEBASE_AUDIT.md
- **NOTE:** Check if my JSON parsing logging fix addressed this

#### P0-12: Wrong timeout exception in automation.py
- **File:** `src/browser/automation.py`
- **Line:** 124
- **Issue:** Imports PlaywrightTimeout but catches TimeoutError (built-in)
- **Impact:** Phantom popup timeout treated as generic error
- **Fix:** Catch `PlaywrightTimeout` instead
- **Audit:** BROWSER_CODEBASE_AUDIT.md

#### P0-13: sys.path mutation in BrowserBridge._do_connect()
- **File:** `src/browser/bridge.py`
- **Issue:** Mutates sys.path at runtime before importing browser.manager
- **Impact:** Can change import precedence, surprising module resolution
- **Fix:** Remove sys.path mutation, fix imports structurally
- **Audit:** BROWSER_CODEBASE_AUDIT.md

### Sources (2 issues)

#### P0-14: socketio_parser unreachable duplicate code
- **File:** `src/sources/socketio_parser.py`
- **Issue:** `_parse_event()` has return None followed by unreachable try block
- **Impact:** Incomplete refactor, possible parsing defects
- **Fix:** Remove unreachable code, add unit tests
- **Audit:** SOURCES_CODE_AUDIT.md

#### P0-15: PriceHistoryHandler double-finalization
- **File:** `src/sources/price_history_handler.py`
- **Issue:** handle_game_end() calls _finalize_game() but doesn't reset state, next game triggers duplicate finalization
- **Impact:** Duplicate "game complete" events, incorrect peak_multiplier
- **Fix:** Reset state after finalization or add finalized flag
- **Audit:** SOURCES_CODE_AUDIT.md

### Config/Main (2 issues)

#### P0-16: Invalid CDP_PORT crashes at import
- **File:** `src/config.py`
- **Issue:** `int(os.getenv("CDP_PORT", "9222"))` crashes if CDP_PORT is non-integer
- **Impact:** App fails before logging/UI initialized
- **Fix:** Use `_safe_int_env("CDP_PORT", 9222, 1, 65535)`
- **Audit:** SRC_CODEBASE_AUDIT.md

#### P0-17: signal.SIGALRM Unix-only (Windows crash)
- **File:** `src/main.py`
- **Issue:** shutdown() uses signal.SIGALRM which doesn't exist on Windows
- **Impact:** AttributeError on Windows shutdown
- **Fix:** Guard with `hasattr(signal, "SIGALRM")` or use thread-based timeout
- **Audit:** SRC_CODEBASE_AUDIT.md

### Services (4 issues)

#### P0-18: DuckDB SQL injection
- **File:** `src/services/event_store/duckdb.py`
- **Issue:** game IDs interpolated into SQL directly, limit via f-string
- **Impact:** Single quote in game_id breaks query, malicious IDs could inject SQL
- **Fix:** Use parameterized queries, DuckDB list params
- **Audit:** SERVICES_CODE_AUDIT.md

#### P0-19: Filename path traversal (username)
- **Files:** `src/services/recorders.py`, `src/services/unified_recorder.py`
- **Issue:** Username incorporated into filename without sanitization
- **Impact:** Username with `/`, `..`, `:` can create wrong paths/overwrites
- **Fix:** Sanitize username (allowlist `[A-Za-z0-9._-]`, replace others with `_`)
- **Audit:** SERVICES_CODE_AUDIT.md

#### P0-20: vector_indexer sys.path injection
- **File:** `src/services/vector_indexer/indexer.py`
- **Issue:** Mutates sys.path to import from ~/Desktop/claude-flow/rag-pipeline
- **Impact:** Not portable, can load arbitrary code
- **Fix:** Package RAG pipeline as dependency or move path mutation behind explicit gate
- **Audit:** SERVICES_CODE_AUDIT.md

#### P0-21: json.dumps() crashes on non-serializable types
- **File:** `src/services/vector_indexer/chunker.py`
- **Issue:** `json.dumps(data, indent=2)` without `default=str` crashes on Decimals/timestamps
- **Impact:** Indexing fails on real Parquet data
- **Fix:** Use `json.dumps(data, indent=2, default=str)`
- **Audit:** SERVICES_CODE_AUDIT.md

### ML (1 issue - conditional)

#### P0-22: ML import-time dependency crash
- **File:** `src/ml/__init__.py`, `src/ml/model.py`
- **Issue:** Imports sklearn/joblib at module import time, crashes if not installed
- **Impact:** Breaks environments without ML extras
- **Fix:** Move heavy imports inside functions or provide clear ImportError message
- **Audit:** ML_CODE_AUDIT.md
- **NOTE:** Only fix if ML is supposed to be optional

---

## 🟡 P1 - THREAD SAFETY & DATA INTEGRITY (High Priority - 16 Issues)

These cause silent failures, race conditions, data loss, or security issues.

### UI (4 issues)

#### P1-1: BrowserConnectionDialog Tkinter thread safety
- **File:** `src/ui/browser_connection_dialog.py`
- **Lines:** 150-253
- **Issue:** _connect_async() runs in background thread and calls Tkinter methods directly
- **Impact:** TclError crashes, UI state corruption
- **Fix:** Marshal all UI updates through root.after()
- **Audit:** UI_CODEBASE_AUDIT.md

#### P1-2: LiveFeedController tick coalescing drops data
- **File:** `src/ui/controllers/live_feed_controller.py`
- **Lines:** 67-131
- **Issue:** Only keeps latest signal, processes max 3 per cycle
- **Impact:** Skips ticks under load → wrong P&L, rug detection, bot decisions
- **Fix:** Either don't drop ticks or make it explicit (UI-only)
- **Audit:** UI_CODEBASE_AUDIT.md

#### P1-3: Heavy work blocks Tk main thread
- **Files:** `src/ui/handlers/capture_handlers.py:74-80`, `src/ui/handlers/replay_handlers.py:33-36`
- **Issue:** subprocess.run() blocks up to 30s, chart redraw on every tick
- **Impact:** UI freezes
- **Fix:** Run subprocess off-thread, throttle chart redraws to 10-20 Hz
- **Audit:** UI_CODEBASE_AUDIT.md

#### P1-4: Live feed connection toggle race
- **File:** `src/ui/controllers/live_feed_controller.py:289-323`
- **Issue:** Connect runs in background thread, disable_live_feed() can clear object on UI thread
- **Impact:** "Connect completes after user disabled" crashes
- **Fix:** Synchronize state checks
- **Audit:** UI_CODEBASE_AUDIT.md

### Core (5 issues)

#### P1-5: GameState observer callbacks run under lock
- **File:** `src/core/game_state.py`
- **Lines:** 413-678, 829-841
- **Issue:** _emit() called from within `with self._lock:`, callbacks can deadlock
- **Impact:** Priority inversion, deadlocks when callbacks interact with UI/other locks
- **Fix:** Collect events, dispatch after releasing lock
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P1-6: DemoRecorder confirmation not flushed
- **File:** `src/core/demo_recorder.py`
- **Lines:** 395-435
- **Issue:** record_confirmation() updates in-memory buffer only, no flush
- **Impact:** Confirmation data lost on crash
- **Fix:** Call _flush() after confirmation or add time-based flush
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P1-7: DemoRecorder filename uses unsanitized game_id
- **File:** `src/core/demo_recorder.py`
- **Lines:** 245-248
- **Issue:** game_id used directly in filename without sanitization
- **Impact:** Path separators/`..` can create wrong paths
- **Fix:** Sanitize game_id (allowlist `[a-zA-Z0-9._-]`)
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P1-8: FileDirectorySource path traversal
- **File:** `src/core/replay_source.py`
- **Lines:** 177-186
- **Issue:** _resolve_path() doesn't prevent `../` in identifier
- **Impact:** Can read arbitrary files if identifier from user input
- **Fix:** Verify `resolved_path.is_relative_to(self.directory.resolve())`
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P1-9: ReplayEngine publishes from multiple threads
- **File:** `src/core/replay_engine.py`
- **Lines:** 412-568
- **Issue:** event_bus.publish() called from playback thread and live feed pushes
- **Impact:** Subscribers run on wrong threads, unsafe for Tkinter
- **Fix:** Confirm EventBus marshals to UI thread or wrap publishes
- **Audit:** CORE_CODEBASE_AUDIT.md

### Sources (2 issues)

#### P1-10: feed_monitors latency logging not rate-limited
- **File:** `src/sources/feed_monitors.py`
- **Issue:** check_latency() logs WARNING/ERROR/CRITICAL on every call, _maybe_emit_status() only rate-limits payload
- **Impact:** Log spam under sustained high latency
- **Fix:** Only log when _maybe_emit_status() emits
- **Audit:** SOURCES_CODE_AUDIT.md

#### P1-11: CDP connection state not updated
- **File:** `src/sources/cdp_websocket_interceptor.py`
- **Issue:** _handle_websocket_closed() clears rugs_websocket_id but not is_connected
- **Impact:** Downstream thinks interception active when it's not
- **Fix:** Update is_connected consistently
- **Audit:** SOURCES_CODE_AUDIT.md

### Services (3 issues)

#### P1-12: EventSourceManager publishes under lock
- **File:** `src/services/event_source_manager.py`
- **Issue:** switch_to_best_source() holds _lock while calling event_bus.publish()
- **Impact:** Deadlock if callbacks call back into EventSourceManager
- **Fix:** Release lock before publishing
- **Audit:** SERVICES_CODE_AUDIT.md

#### P1-13: CDPBrowserManager stderr PIPE blocking
- **File:** `src/browser/manager.py`
- **Issue:** Uses stderr=PIPE but never drains it
- **Impact:** Chrome can hang if stderr buffer fills
- **Fix:** Redirect to file or read in background thread
- **Audit:** BROWSER_CODEBASE_AUDIT.md

#### P1-14: UnifiedRecorder action-file handle leak
- **File:** `src/services/unified_recorder.py`
- **Issue:** _start_game_recording() opens file, not closed if stop_session() doesn't finalize
- **Impact:** File handle leak on abnormal shutdown
- **Fix:** Close in stop_session() or shutdown()
- **Audit:** SERVICES_CODE_AUDIT.md

### Config/Main (2 issues)

#### P1-15: Config.save_to_file() doesn't persist "files" section
- **File:** `src/config.py`
- **Issue:** load_from_file() supports "files" section, save_to_file() omits it
- **Impact:** File path overrides don't persist
- **Fix:** Add "files" to save_to_file()
- **Audit:** SRC_CODEBASE_AUDIT.md

#### P1-16: Config JSON round-trip corrupts types
- **File:** `src/config.py`
- **Issue:** frozenset/tuples become strings via `default=str`, not restored
- **Impact:** Runtime bugs if code expects original type
- **Fix:** Extend tagged serialization or enforce JSON-only types
- **Audit:** SRC_CODEBASE_AUDIT.md

---

## 🟠 P2 - CODE QUALITY & CORRECTNESS (Medium Priority - 28 Issues)

These are important but won't crash immediately. Fix when practical.

### Models (3 issues)

#### P2-1: Latency calculations inverted
- **File:** `src/models/events/trade_events.py`
- **Lines:** 136, 220
- **Issue:** calculate_latency() returns `client_timestamp - self.timestamp` (likely negative)
- **Fix:** Return positive duration by convention
- **Audit:** MODELS_CODE_AUDIT.md

#### P2-2: is_whale_trade @property with parameter
- **File:** `src/models/events/trade_events.py`
- **Issue:** Property can't accept threshold parameter
- **Fix:** Remove @property or remove parameter
- **Audit:** MODELS_CODE_AUDIT.md

#### P2-3: Timestamp timezone inconsistency
- **Files:** Multiple (models/events/, recording_models.py, etc.)
- **Issue:** Mix of naive (utcnow()) and aware UTC timestamps
- **Fix:** Standardize on timezone-aware UTC
- **Audit:** MODELS_CODE_AUDIT.md

### Browser (4 issues)

#### P2-4: BrowserExecutor float math for Decimals
- **File:** `src/browser/executor.py`
- **Issue:** Uses float + round(..., 3) for Decimal amounts
- **Impact:** Drift from intended Decimal values
- **Fix:** Use integer milli-SOL arithmetic or Decimal quantization
- **Audit:** BROWSER_CODEBASE_AUDIT.md

#### P2-5: DOM parsing fragile
- **Files:** `src/browser/executor.py` (read_balance_from_browser, read_position_from_browser)
- **Issue:** Regex assumes decimal dot, can miss `1` or localized formats
- **Fix:** Improve number extraction regex
- **Audit:** BROWSER_CODEBASE_AUDIT.md

#### P2-6: Wallet detection too permissive
- **File:** `src/browser/automation.py`
- **Issue:** Regex `[A-Za-z0-9]{32,}` matches any 32+ alphanumeric string
- **Impact:** False positives skip wallet connect
- **Fix:** Use Solana address format validation
- **Audit:** BROWSER_CODEBASE_AUDIT.md

#### P2-7: Duplicate selector sources
- **Files:** `src/browser/dom/selectors.py`, `src/browser/bridge.py`
- **Issue:** Selectors defined in two places
- **Impact:** Divergence, bug fixes land in one path not both
- **Fix:** Centralize selectors
- **Audit:** BROWSER_CODEBASE_AUDIT.md

### Core (4 issues)

#### P2-8: Dual rug flags confusing
- **File:** `src/core/game_state.py`
- **Issue:** `rugged` vs `rug_detected` easy to mix up
- **Fix:** Rename for clarity or consolidate
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P2-9: Amount/price semantics unclear
- **Files:** `src/core/game_state.py`, `src/models/game_tick.py`, `src/core/validators.py`
- **Issue:** Unclear if amount is "exposure units" or "SOL invested"
- **Fix:** Tighten naming/documentation
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P2-10: RecorderSink counts characters not bytes
- **File:** `src/core/recorder_sink.py`
- **Lines:** 363-367
- **Issue:** total_bytes_written is character count
- **Impact:** Misleading metrics (not a correctness issue)
- **Fix:** Document as character count or track bytes
- **Audit:** CORE_CODEBASE_AUDIT.md

#### P2-11: SessionState corruption handling
- **File:** `src/core/session_state.py`
- **Lines:** 93-99
- **Issue:** JSONDecodeError just returns defaults, doesn't backup corrupt file
- **Fix:** Backup corrupt file before rewriting
- **Audit:** CORE_CODEBASE_AUDIT.md

### Services (5 issues)

#### P2-12: StateVerifier type normalization
- **File:** `src/services/state_verifier.py`
- **Issue:** Assumes server values are Decimal-compatible, may crash on str/float
- **Fix:** Normalize via `Decimal(str(...))`
- **Audit:** SERVICES_CODE_AUDIT.md

#### P2-13: EventBus stats race
- **File:** `src/services/event_bus.py`
- **Issue:** _stats mutated by processing thread without lock
- **Fix:** Document as approximate or add lock
- **Audit:** SERVICES_CODE_AUDIT.md

#### P2-14: AsyncLoopManager lifecycle
- **File:** `src/services/async_loop_manager.py`
- **Issue:** Busy-wait startup, __del__ calls stop()
- **Fix:** Use threading.Event for startup, avoid __del__ cleanup
- **Audit:** SERVICES_CODE_AUDIT.md

#### P2-15: Logging service not concurrency-safe
- **File:** `src/services/logger.py`
- **Issue:** setup_logging() not protected by lock
- **Fix:** Add lock or make idempotent
- **Audit:** SERVICES_CODE_AUDIT.md

#### P2-16: service.py.backup in repo
- **File:** `src/services/event_store/service.py.backup`
- **Issue:** Backup file shouldn't be in runtime source
- **Fix:** Remove from repo
- **Audit:** SERVICES_CODE_AUDIT.md

### Utils (4 issues)

#### P2-17: to_decimal() logging noisy
- **File:** `src/utils/decimal_utils.py`
- **Issue:** Logs warning on every conversion failure in hot paths
- **Fix:** Make logging optional or downgrade to debug
- **Audit:** UTILS_CODE_AUDIT.md

#### P2-18: Numeric type includes bool
- **File:** `src/utils/decimal_utils.py`
- **Issue:** bool subclass of int, to_float(True) becomes 1.0
- **Fix:** Explicitly reject booleans
- **Audit:** UTILS_CODE_AUDIT.md

#### P2-19: safe_divide() not safe for None
- **File:** `src/utils/decimal_utils.py`
- **Issue:** Crashes if either input is None
- **Fix:** Accept `Numeric | None` or rename
- **Audit:** UTILS_CODE_AUDIT.md

#### P2-20: Rounding defaults inconsistent
- **File:** `src/utils/decimal_utils.py`
- **Issue:** SOL_PRECISION=9 but round_sol() defaults to 4dp
- **Fix:** Clarify UI vs native precision
- **Audit:** UTILS_CODE_AUDIT.md

### ML (4 issues)

#### P2-21: Backtester cooldown off by 5 ticks
- **File:** `src/ml/backtest.py`
- **Issue:** Enforces >=50 ticks between bets, not 45
- **Fix:** Correct to 45 or update docs
- **Audit:** ML_CODE_AUDIT.md

#### P2-22: SidebetModel.train() breaks on single-class
- **File:** `src/ml/model.py`
- **Issue:** compute_class_weight crashes if only one class
- **Fix:** Validate y contains both classes upfront
- **Audit:** ML_CODE_AUDIT.md

#### P2-23: SidebetPredictor uses lowercase `any`
- **File:** `src/ml/predictor.py`
- **Issue:** `dict[str, any]` should be `dict[str, Any]`
- **Fix:** Import and use `Any` from typing
- **Audit:** ML_CODE_AUDIT.md

#### P2-24: GameDataProcessor memory-heavy
- **File:** `src/ml/data_processor.py`
- **Issue:** Loads entire JSONL into memory
- **Fix:** Stream line-by-line
- **Audit:** ML_CODE_AUDIT.md

### Debug (3 issues)

#### P2-25: Debug callbacks on background threads
- **File:** `src/debug/raw_capture_recorder.py`
- **Issue:** on_capture_stopped invoked from background thread without try/except
- **Fix:** Wrap in try/except, document thread safety
- **Audit:** DEBUG_CODE_AUDIT.md

#### P2-26: stop_capture() callback timing async
- **File:** `src/debug/raw_capture_recorder.py`
- **Issue:** Returns before callback fires
- **Fix:** Call callback synchronously or offer blocking option
- **Audit:** DEBUG_CODE_AUDIT.md

#### P2-27: Debug import style
- **File:** `src/debug/__init__.py`
- **Issue:** Uses `from debug.` instead of relative import
- **Fix:** Use `from .raw_capture_recorder import ...`
- **Audit:** DEBUG_CODE_AUDIT.md

### Config/Main (1 issue)

#### P2-28: sys.path injection can shadow modules
- **File:** `src/main.py`
- **Issue:** Inserts repo parent at sys.path[0]
- **Impact:** Non-deterministic imports if overlapping module names
- **Fix:** Avoid sys.path mutation or insert src/ only
- **Audit:** SRC_CODEBASE_AUDIT.md

---

## 📊 SUMMARY

### By Priority:
- **✅ Completed:** 9 bug categories (my fixes)
- **🔴 P0 Runtime Crashes:** 22 issues (MUST FIX IMMEDIATELY)
- **🟡 P1 Thread Safety / Data Integrity:** 16 issues (HIGH PRIORITY)
- **🟠 P2 Code Quality / Correctness:** 28 issues (MEDIUM PRIORITY)

### By Category:
- **Models:** 4 issues (1 P0, 3 P2)
- **Core:** 13 issues (4 P0, 5 P1, 4 P2)
- **UI:** 9 issues (5 P0, 4 P1)
- **Browser:** 8 issues (3 P0, 1 P1, 4 P2)
- **Sources:** 4 issues (2 P0, 2 P1)
- **Services:** 12 issues (4 P0, 3 P1, 5 P2)
- **Config/Main:** 5 issues (2 P0, 2 P1, 1 P2)
- **Utils:** 4 issues (all P2)
- **ML:** 5 issues (1 P0, 4 P2)
- **Debug:** 3 issues (all P2)

### Total: 67 issues remaining + 9 completed = 76 total issues identified

---

## 🎯 RECOMMENDED FIX ORDER

### Phase 1: P0 Runtime Crashes (Highest Impact)
1. Fix isinstance syntax error (P0-1) - 1 line change
2. Fix TradeManager sidebet dict access (P0-2) - affects trading
3. Fix GameState.get_current_tick() field (P0-3) - affects rug detection
4. Fix all 5 UI AttributeErrors/TypeErrors (P0-6 through P0-10) - common paths
5. Fix CDP_PORT validation (P0-16) - import-time crash
6. Fix Windows signal.SIGALRM (P0-17) - portability
7. Fix WS_RAW_EVENT double-wrapping (P0-11) - check overlap with my fix
8. Fix DuckDB SQL injection (P0-18) - security
9. Fix filename path traversal (P0-19) - security

### Phase 2: P1 Thread Safety & Data Integrity
10. Fix BrowserConnectionDialog thread safety (P1-1) - Tk violations
11. Fix LiveFeedController tick coalescing (P1-2) - data loss
12. Fix GameState observer deadlock (P1-5) - concurrency
13. Fix path traversal vulnerabilities (P1-7, P1-8) - security
14. Fix heavy Tk blocking (P1-3) - user experience

### Phase 3: P2 Code Quality
15. Address P2 issues during normal development as encountered

---

## 📝 NEXT STEPS

1. **Review this list** - Verify priorities with user
2. **Create GitHub issues** - One per P0/P1 item for tracking
3. **Fix P0 issues first** - Start with Phase 1 items 1-9
4. **Run test suite** - After each fix to verify no regressions
5. **Commit incrementally** - Clear messages referencing issue numbers
6. **Push and create PR** - When P0 issues complete

---

**Generated:** 2025-12-22
**Author:** Claude Code (Automated Audit Cross-Reference)
**Audit Sources:**
- My COMPREHENSIVE_AUDIT_REPORT.md + FIXES_COMPLETED.md
- Newly merged audit files (11 files in src/ subdirectories)
