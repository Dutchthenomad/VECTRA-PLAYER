# UI Codebase Audit (`src/ui`)

Date: 2025-12-22

## Scope

Audited Python modules under `src/ui/` (including subpackages):

- `src/ui/*.py`
- `src/ui/builders/*.py`
- `src/ui/controllers/*.py`
- `src/ui/handlers/*.py`
- `src/ui/interactions/*.py`
- `src/ui/widgets/*.py`
- `src/ui/window/*.py`

Out of scope: non-UI packages (`src/services`, `src/core`, `src/models`, etc.) except where required to reason about UI behavior and integration risks.

## Methodology

- Manual review focused on UI thread-safety (Tkinter), controller lifecycles, event subscription/disposal, and blocking I/O on the UI thread.
- Pattern scans for threading, `asyncio`, subprocess usage, broad exception handling, and conflict markers.
- Syntax check: `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile src/ui/**/*.py`
- UI tests attempt:
  - `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_ui`
    - Fails at collection due to missing dependency `duckdb` (see `tests/test_ui/test_capture_stats.py`).
  - `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_ui --ignore=tests/test_ui/test_capture_stats.py`
    - Runs, but **all tests were skipped** in this environment (likely headless / no display).

## Executive Summary

The UI layer is reasonably modular (controllers + handlers + builders), and many background-to-UI transitions correctly use `root.after()` / `TkDispatcher`.

However, there are multiple **high-risk runtime bugs** and **UI thread-safety violations** that can crash the app or silently desynchronize state (especially in live mode). Several issues are integration mismatches with `core` and `services` that are not protected by tests in this environment.

## Findings (Prioritized)

### A) Confirmed Bugs / Guaranteed Runtime Exceptions

1) `BotManager.toggle_bot()` assumes `current_tick` is an object with `.active`

- Where: `src/ui/controllers/bot_manager.py:116-120`
- What: `current_tick = self.state.get("current_tick")` is an `int` in `core.GameState`, but code uses `current_tick.active`.
- Impact: when disabling the bot during an active game (tick > 0), this can throw `AttributeError` and break UI state restoration.

2) `BotManager.show_bot_config()` calls toast with unsupported kwargs (`bootstyle`)

- Where: `src/ui/controllers/bot_manager.py:176-181`
- What: `self.toast` is `ui/widgets/toast_notification.ToastNotification`, which has `show(message, msg_type, duration)` and does not accept `bootstyle`.
- Impact: config update path will crash with `TypeError: show() got an unexpected keyword argument 'bootstyle'`.

3) `LiveFeedController` calls nonexistent `ReplayEngine.set_seed_data()`

- Where: `src/ui/controllers/live_feed_controller.py:232-239`
- What: `ReplayEngine` in `src/core/replay_engine.py` does not define `set_seed_data`.
- Impact: when `gameComplete` arrives with `seedData`, Tk callback will raise `AttributeError`, likely surfacing as an uncaught Tkinter callback exception.

4) Legacy browser connection dialog is constructed with wrong signature

- Where: `src/ui/controllers/browser_bridge_controller.py:73-78`
- What: `BrowserConnectionDialog.__init__` requires `browser_executor` (`src/ui/browser_connection_dialog.py:25`), but caller does not pass it.
- Impact: calling the legacy dialog will raise `TypeError` immediately.

5) `RecordingController.start_session()` calls nonexistent `RecordingToastManager.show()`

- Where: `src/ui/controllers/recording_controller.py:157-161`
- What: `RecordingToastManager` (from `src/ui/toast_notification.py`) has methods like `recording_started()`, not `show()`.
- Impact: if `RUGS_LEGACY_RECORDERS=false`, the “EventStore-only mode” path will raise `AttributeError`.

### B) UI Thread-Safety / Concurrency Hazards

1) `BrowserConnectionDialog` performs Tk operations from a background thread

- Where:
  - UI mutations in `_log_progress()` (`src/ui/browser_connection_dialog.py:150-160`)
  - `_connect_async()` calls `_log_progress()` repeatedly (`src/ui/browser_connection_dialog.py:170-223`)
  - `_connect_async()` is executed inside a background thread loop (`src/ui/browser_connection_dialog.py:235-253`)
- Impact:
  - Tkinter is not thread-safe; updating `Text`, calling `dialog.update()`, etc. from a non-main thread can crash with `TclError` or corrupt UI state.
- Additional risk: `self.dialog.update()` (`src/ui/browser_connection_dialog.py:159`) can re-enter the event loop and cause hard-to-debug reentrancy problems even on the main thread.

2) Live feed “coalescing” can drop ticks and corrupt state/recording

- Where: `src/ui/controllers/live_feed_controller.py:67-123`
- What: only the latest signal is kept (`_latest_signal`), and the drain processes at most 3 per cycle.
- Impact:
  - If “signal” events correspond to game ticks, this can **skip ticks** under load, affecting:
    - rug detection timing,
    - P&L calculations,
    - bot decisions,
    - any “record every tick” assumption.
  - If dropping is intended, it should be explicit and limited to UI rendering, not the core tick ingestion path.

3) Heavy work on the Tk main thread (risk of freezes)

- `CaptureHandlersMixin._analyze_last_capture()` blocks up to 30s via `subprocess.run()` on the UI thread (`src/ui/handlers/capture_handlers.py:74-80`).
- `ReplayHandlersMixin._process_tick_ui()` does a full chart redraw each tick via `ChartWidget.add_tick()` → `draw()` (`src/ui/handlers/replay_handlers.py:33-36`, `src/ui/widgets/chart.py:176-191`).
- `LiveFeedController._drain_live_signals()` calls `ReplayEngine.push_tick()` in the UI thread (`src/ui/controllers/live_feed_controller.py:124-131`); `push_tick()` can do non-trivial work (locking, event publishing, optional disk recording).

4) Connection toggle race: connect thread vs user toggling off

- Where: connect runs in a background thread (`src/ui/controllers/live_feed_controller.py:289-309`), but `disable_live_feed()` can clear `self.parent.live_feed` on the UI thread (`src/ui/controllers/live_feed_controller.py:323+`).
- Impact: “connect completes after user disabled” or “disconnect called on partially-initialized object” edge cases.

### C) Integration/API Contract Risks (UI ↔ Core/Services)

1) UI tick handler calls `TradeManager.check_and_handle_rug()` / `check_sidebet_expiry()` which are currently broken

- Where: `src/ui/handlers/replay_handlers.py:35-36`
- Why: `core.TradeManager` currently treats sidebets as objects, but `GameState` stores them as dicts (see core audit).
- Impact: a rug tick while a sidebet exists can raise `AttributeError` during UI tick processing.

2) `MainWindow` hard-imports `EventStoreService` (which imports `duckdb`)

- Where: `src/ui/main_window.py:24-26`
- Impact:
  - In environments without `duckdb`, importing the UI may fail.
  - This prevented UI tests from collecting (`tests/test_ui/test_capture_stats.py` import path).
- Recommendation: if `duckdb` is optional, delay-import or guard behind feature flags; otherwise ensure it is an explicit runtime dependency.

3) `RecordingController.start_session()` “game in progress” detection is likely wrong

- Where: `src/ui/controllers/recording_controller.py:185-191`
- What: uses `self.game_state.get_current_tick() is not None`, but `GameState.get_current_tick()` always constructs a `GameTick` even when no game is loaded.
- Impact: recorder may always start as “game in progress”, affecting session state machine behavior.

4) Mixed toast implementations create inconsistent call sites

- `src/ui/widgets/toast_notification.py` (simple Toplevel toasts) vs `src/ui/toast_notification.py` (stacking Frame + `RecordingToastManager`).
- Evidence:
  - Main window uses `ui.widgets.ToastNotification` (`src/ui/main_window.py:38`)
  - Recording uses `RecordingToastManager` (`src/ui/controllers/recording_controller.py:31-33`)
  - Bot manager tries to call a third-party style (`bootstyle`) on the widgets toast (`src/ui/controllers/bot_manager.py:176-181`)
- Impact: API mismatches and inconsistent UX.

### D) Data Integrity / Safety / Portability

1) Non-portable shell integration

- Uses `xdg-open` directly on Linux in multiple places (`src/ui/handlers/capture_handlers.py:98`, `src/ui/controllers/replay_controller.py:197+`).
- If cross-platform support is a goal, centralize this behavior and fallback gracefully.

2) `ChartWidget` log scale math can crash on zero/negative prices

- Where: `src/ui/widgets/chart.py:213-218` (`math.log10(float(self.min_price))`)
- Risk: if any visible tick has `price <= 0`, log10 will raise.
- Note: `price_to_y()` clamps `price <= 0`, but `_update_price_range()` does not clamp `min_price`/`max_price`.

3) Event bus usage split between injected and singleton instances

- Example: debug terminal uses `from services.event_bus import event_bus` rather than `self.event_bus` (`src/ui/handlers/capture_handlers.py:146-168`).
- Risk: if multiple buses exist (tests, future refactors), subscriptions can go to the wrong instance.

## Strengths / Improvements Observed

- Many background callbacks correctly marshal UI updates through `root.after()` or `ui_dispatcher.submit()` (e.g., live feed handlers).
- `TimingOverlay.update_stats()` is explicitly thread-safe via `parent.after()` (`src/ui/timing_overlay.py:273-327`).
- `LiveFeedController` snapshots inbound events before scheduling UI work to reduce mutation races (`src/ui/controllers/live_feed_controller.py:157-170` and related handlers).

## Suggested Next Steps (Highest ROI)

1) Fix hard runtime crashes:
   - `BotManager` tick type (`src/ui/controllers/bot_manager.py:116`)
   - toast API mismatch (`src/ui/controllers/bot_manager.py:176`)
   - remove/implement `ReplayEngine.set_seed_data` call (`src/ui/controllers/live_feed_controller.py:238`)
   - fix `BrowserConnectionDialog` construction (`src/ui/controllers/browser_bridge_controller.py:73`)
   - fix `_toast.show` in `RecordingController` (`src/ui/controllers/recording_controller.py:160`)
2) Enforce Tkinter thread confinement:
   - refactor `BrowserConnectionDialog` so `_connect_async()` never touches widgets off the main thread.
3) Decide the live tick ingestion contract:
   - if every tick matters for correctness/recording, do not drop them in `LiveFeedController` coalescing.
4) Prevent UI freezes:
   - run `subprocess.run()` work off-thread and stream results back to UI.
   - throttle chart redraws (e.g., redraw at 10–20 Hz instead of every tick).
5) Make dependencies explicit:
   - either require `duckdb` for the UI runtime or guard imports so headless/unit tests can still collect.

## Appendix

### Commands run

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(find src/ui -type f -name "*.py")`
- `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_ui`
  - Failed: `ModuleNotFoundError: No module named 'duckdb'` during collection.
- `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_ui --ignore=tests/test_ui/test_capture_stats.py`
  - Result: tests collected but **91 skipped** in this environment.
