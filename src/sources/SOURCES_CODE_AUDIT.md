# Sources Code Audit Report (`src/sources/`)

Date: 2025-12-22
Scope: All source files under `src/sources/`.
Method: Manual static review + `python3 -m compileall -q src/sources` (syntax check).

## Executive Summary

The `sources/` package is generally well-structured after modularization, with clear separations for parsing (`socketio_parser.py`), health monitoring (`feed_monitors.py`), rate limiting (`feed_rate_limiter.py`), degradation control (`feed_degradation.py`), integrity tracking (`data_integrity_monitor.py`), and a high-level live transport (`websocket_feed.py`) plus CDP capture (`cdp_websocket_interceptor.py`).

The most critical issues found:

- `socketio_parser.py` contains unreachable duplicate code after a `return`, which is a strong signal of an incomplete refactor and can hide real parsing bugs.
- `price_history_handler.py` can emit “game complete” twice for the same game and can miss applying `partialPrices` beyond current buffer length; peak tracking can also be wrong when gap-filling.
- `feed_monitors.py`’s latency detector rate-limits the *returned spike status*, but still logs warnings/errors on every call, which can spam logs under sustained bad conditions.
- `cdp_websocket_interceptor.py`’s connection state can become inconsistent (e.g., WebSocket closed but `is_connected` remains `True`) and repeated `connect()` calls can register duplicate CDP handlers.

No syntax errors were found.

## Inventory (Files Reviewed)

- `src/sources/__init__.py`
- `src/sources/cdp_websocket_interceptor.py`
- `src/sources/data_integrity_monitor.py`
- `src/sources/feed_degradation.py`
- `src/sources/feed_monitors.py`
- `src/sources/feed_rate_limiter.py`
- `src/sources/game_state_machine.py`
- `src/sources/price_history_handler.py`
- `src/sources/socketio_parser.py`
- `src/sources/websocket_feed.py`

Non-runtime artifacts present in-tree:
- `src/sources/__pycache__/...` (bytecode cache directory)

## High Priority Findings (Fix Soon)

### 1) `socketio_parser.py`: unreachable duplicate parsing code

**Why this matters**
- `_parse_event()` has a `return None` followed by another `try:` block that will never execute.
- This is a correctness smell: it suggests the parser was modified but old code was not removed, increasing the chance of subtle parsing defects (e.g., around namespaces/ack IDs).

**Where**
- `src/sources/socketio_parser.py` (`_parse_event`)

**Recommended remediation**
- Remove the unreachable block.
- Add small unit tests for representative frames:
  - `42["event", {...}]`
  - `42123["event", {...}]` (ack id)
  - `42/namespace,["event", {...}]`
  - invalid JSON / missing brackets

### 2) `price_history_handler.py`: double-finalization and incomplete gap fill

**Why this matters**
- `handle_game_end()` calls `_finalize_game()`, but does not reset `current_game_id`/buffers.
- Later, the next game’s first tick triggers `handle_tick()`’s “new game started” branch and calls `_finalize_game()` again for the previous game, causing duplicate “game complete” emission.
- `handle_partial_prices()` ignores ticks beyond the current list length; if partial prices contain new ticks you didn’t receive individually, you’ll silently drop them.
- Gap-filling does not update `peak_multiplier`, so the emitted `peak_multiplier` can be understated if the highest price was only seen via `partialPrices`.

**Where**
- `src/sources/price_history_handler.py` (`handle_game_end`, `handle_tick`, `handle_partial_prices`)

**Recommended remediation**
- After `_finalize_game()`, reset state (`current_game_id = None`, clear buffers) or add a “finalized” flag to prevent duplicate emits.
- In `handle_partial_prices()`, extend `self.prices` to cover new tick indices and update peak tracking.

### 3) `feed_monitors.py`: latency logging is not rate-limited

**Why this matters**
- `LatencySpikeDetector.record()` calls `check_latency()`, which logs at WARNING/ERROR/CRITICAL levels immediately.
- `_maybe_emit_status()` rate-limits the returned “spike info” payload, but the logger output still happens per-sample.
- Under sustained high latency (or intermittent spikes), this can spam logs and hide more actionable events.

**Where**
- `src/sources/feed_monitors.py` (`LatencySpikeDetector.check_latency`)

**Recommended remediation**
- Make `check_latency()` a pure classifier (no logging), and log only when `_maybe_emit_status()` decides to emit.
- Alternatively, add the same cooldown gating to the logging path.

### 4) `cdp_websocket_interceptor.py`: connection state and handler lifecycle concerns

**Why this matters**
- `_handle_websocket_closed()` clears `rugs_websocket_id` but does not update `is_connected`, so downstream code can think interception is active when it is not.
- `connect()` registers CDP event handlers each time; repeated `connect()` calls can result in duplicate callbacks unless you unhook or guard.
- `disconnect()` disables Network but does not explicitly detach event listeners (depends on CDP client behavior).

**Where**
- `src/sources/cdp_websocket_interceptor.py` (`connect`, `_handle_websocket_closed`, `disconnect`)

**Recommended remediation**
- Update `is_connected` consistently when the tracked WebSocket closes (or introduce separate states like “cdp_attached” vs “ws_tracked”).
- Add a guard to prevent double registration or detach handlers on disconnect if the CDP client supports it.

## Medium Priority Findings (Fix When Practical)

### 5) `data_integrity_monitor.py`: tick regression/duplication behavior is undefined

**Why this matters**
- `on_tick()` handles only `tick > expected` and `tick == expected`.
- If ticks are duplicated (same tick repeated) or regress (tick decreases), the monitor does not reset or explicitly handle it; it just sets `_last_tick = tick`.
- This can cause confusing “gap” accounting after a regression or a repeated tick.

**Where**
- `src/sources/data_integrity_monitor.py` (`on_tick`)

**Recommended remediation**
- Decide on expected behavior for duplicate/regressing ticks and implement it explicitly (ignore, reset counters, trigger an issue, etc.).

### 6) `websocket_feed.py`: timestamp/timezone consistency and brittle formatting

**Why this matters**
- `signal_to_game_tick()` uses `datetime.fromtimestamp(...)` without an explicit timezone, producing local-time ISO strings, while other parts of the codebase use UTC semantics.
- `_handle_game_complete()` logs `peakMultiplier` using `:.2f`; if `peakMultiplier` is `None` or a string, this can raise and break the handler (though it’s inside normal handler flow).

**Where**
- `src/sources/websocket_feed.py` (`signal_to_game_tick`, `_handle_game_complete`)

**Recommended remediation**
- Use timezone-aware UTC formatting (e.g., `datetime.fromtimestamp(..., tz=UTC)` or `datetime.utcfromtimestamp(...)`).
- Guard formatting of `peakMultiplier` (normalize to float/Decimal or log without numeric formatting when missing).

### 7) `websocket_feed.py`: logger handler attachment can interfere with app-level logging

**Why this matters**
- The class attaches a `StreamHandler` directly to a named logger (`"WebSocketFeed"`) if no handlers exist.
- In applications with centralized logging configuration (`services/logger.py`), this can cause unexpected output duplication or inconsistent formatting.

**Where**
- `src/sources/websocket_feed.py` (`__init__` logger setup)

**Recommended remediation**
- Prefer using `logging.getLogger(__name__)` and rely on centralized logging setup, or make handler attachment opt-in.

## Low Priority Findings / Opportunities

### 8) `__init__.py`: eager imports increase import side effects and startup cost

**Notes**
- `src/sources/__init__.py` imports most classes, including `WebSocketFeed`.
- This is convenient but makes `import sources` heavier and can trigger more import-time side effects than necessary.

**Where**
- `src/sources/__init__.py`

**Recommendation**
- Consider mirroring `services/__init__.py`’s “lightweight import + lazy exports” pattern if import cost becomes an issue.

### 9) Consistency improvements (types, locks, and error tracking)

**Notes**
- Several modules use `logging` directly instead of module-level `logger`, and several catch `Exception` and `pass` without logging.
- Metrics in `WebSocketFeed` track some errors but not all (e.g., `_emit_event` handler failures are logged but don’t increment metrics).

## Suggested Validation Checklist (After Fixes)

- Run the existing test suite: `cd src && python3 -m pytest tests/ -v`
- Exercise live feed flows:
  - Confirm `socketio_parser.parse_socketio_frame()` handles namespaces and ack IDs as expected.
  - Confirm `PriceHistoryHandler` emits exactly once per game and produces complete price arrays when partial prices are present.
  - Force high-latency scenarios and ensure logs remain readable (rate-limited).
  - Connect/disconnect CDP interception multiple times and verify no duplicated callbacks and correct connection state.
