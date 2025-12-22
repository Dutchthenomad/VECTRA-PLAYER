# Browser Codebase Audit (`src/browser`)

Date: 2025-12-22

## Scope

Audited Python modules under `src/browser/`:

- `src/browser/__init__.py`
- `src/browser/automation.py`
- `src/browser/bridge.py`
- `src/browser/executor.py`
- `src/browser/manager.py`
- `src/browser/profiles.py`
- `src/browser/automation.py`
- `src/browser/dom/selectors.py`
- `src/browser/dom/timing.py`
- `src/browser/cdp/launcher.py` (legacy)

Out of scope: other subsystems (`src/ui`, `src/services`, etc.) except where needed to reason about API contracts.

## Methodology

- Manual review focused on:
  - asyncio/threading correctness and shutdown behavior
  - CDP / Playwright lifecycle reliability
  - UI↔browser API contracts used by `src/ui`
  - correctness of selector/click logic and event forwarding
- Pattern scans for concurrency, subprocess usage, broad exception handling.
- Syntax check: `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(find src/browser -name "*.py")`
- Targeted test run (non-GUI): `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_sources/test_cdp_websocket_interceptor.py`
  - Result: **13 passed** (1 warning).

## Executive Summary

This folder contains the CDP/Playwright automation stack plus the `BrowserBridge` (UI → async loop → CDP). The overall architecture is sensible (queue-based async loop + multi-strategy selectors + timeout wrappers).

However, there are several **high-risk integration bugs** that can break live features immediately, plus a few reliability and correctness issues that can cause hangs, dropped data, or incorrect browser state assumptions.

## Findings (Prioritized)

### A) Confirmed Bugs / High-Likelihood Runtime Errors

1) `WS_RAW_EVENT` publishing shape is wrong (breaks DebugTerminal consumers)

- Where: `src/browser/bridge.py` (event forwarding in `on_cdp_event` near the top of `BrowserBridge.__init__`).
- What:
  - Publishes `self._event_bus.publish(Events.WS_RAW_EVENT, {"data": event})`.
  - EventBus callbacks wrap payload as `{"name": ..., "data": payload}`.
  - UI handler (`src/ui/handlers/capture_handlers.py`) expects `event["data"]` to be the *actual* WebSocket event dict with keys like `"event"`, `"data"`, `"timestamp"`, and passes it straight into `DebugTerminal.log_event()`.
- Impact:
  - Current publishing makes UI receive `{"data": {"data": event}}`, so `DebugTerminal` sees no `"event"` key and logs it as unknown/malformed.
- Fix direction: publish `event` directly (`publish(..., event)`), not `{"data": event}`.

2) `browser/automation.py` catches the wrong timeout exception and ignores its own `timeout` parameter

- Where: `src/browser/automation.py:124` (`page.context.expect_page(timeout=10000)` block).
- What:
  - Imports Playwright timeout as `PlaywrightTimeout`, but the popup wait block catches `TimeoutError` (built-in), not `PlaywrightTimeout`.
  - The function signature has `timeout: int = 30` but the implementation uses hard-coded wait times (`5000`, `3000`, `10000`) and does not apply the `timeout` argument consistently.
- Impact:
  - Phantom popup timeout may be treated as a generic error (caught by outer `except Exception`) rather than a recoverable timeout path.
  - Callers cannot tune connection timing via the exposed parameter.

3) `BrowserBridge._do_connect()` mutates `sys.path` at runtime

- Where: `src/browser/bridge.py` in `_do_connect()`.
- What: prepends a parent directory to `sys.path` before importing `browser.manager`.
- Impact:
  - Can change import precedence and lead to surprising module resolution in long-running processes/tests.
  - Indicates packaging/module path confusion that should be resolved structurally rather than dynamically.

### B) Race Conditions / Shutdown & Lifecycle Risks

1) Background async loop startup failure can leak a thread

- Where: `src/browser/bridge.py:start_async_loop()`.
- What:
  - If `_loop_ready.wait(timeout=5.0)` fails, it sets `_running=False` and returns, but does not join/clean up the newly created thread or event loop.
- Impact: potential leaked daemon thread and inconsistent state (especially during repeated connect attempts).

2) `_queue_action()` uses `asyncio.run_coroutine_threadsafe` without handling loop closure

- Where: `src/browser/bridge.py:_queue_action()`.
- Risk:
  - If `_loop` is closing/closed (shutdown race), `run_coroutine_threadsafe(...)` can raise.
  - Current code logs “cannot queue action” only when `_running` or `_loop` is falsy; it does not guard the “loop exists but is closing” case.
- Impact: intermittent exceptions during app shutdown or rapid connect/disconnect toggles.

3) `CDPBrowserManager` uses `stderr=PIPE` for Chrome but never drains it while running

- Where: `src/browser/manager.py:_launch_chrome()`.
- Risk:
  - If Chrome writes enough stderr output, the pipe buffer can fill and block the Chrome process.
- Impact: rare-but-nasty “Chrome launched but hangs” failure mode. Capturing stderr is useful, but consider redirecting to a file or reading in a background thread.

### C) Reliability / Correctness Risks

1) `BrowserExecutor` uses float math to plan Decimal increments

- Where: `src/browser/executor.py:_build_amount_incrementally_in_browser()`.
- What: converts `Decimal` → `float`, uses `round(..., 3)`.
- Impact:
  - Can miscompute sequences for values that aren’t exactly representable or have >3 decimal places.
  - Produces browser-side amounts that can drift from the intended `Decimal` input.
- Fix direction: use integer “milli-SOL” arithmetic or `Decimal` quantization rather than floats.

2) DOM parsing is fragile (balance/position)

- Where:
  - `src/browser/executor.py:read_balance_from_browser()`
  - `src/browser/executor.py:read_position_from_browser()`
- Risks:
  - Regex for numeric extraction assumes decimals with a dot (e.g., `1.0`), which misses `1` or localized formats.
  - Selector sets mix Playwright selector engines with `query_selector()`; generally okay, but failure modes are silent and hard to debug.

3) Wallet “already connected” heuristics are very permissive

- Where: `src/browser/automation.py:already_connected` check.
- What: treats presence of any `[A-Za-z0-9]{32,}` in body text as a Solana address; can match unrelated content.
- Impact: can produce false positives and skip required wallet connect flow.

4) Source-of-truth split: two parallel browser-control stacks exist

- CDP-first stack: `src/browser/manager.py` + `src/browser/bridge.py` + `src/browser/executor.py`
- Legacy persistent-context stack: `src/browser/cdp/launcher.py`
- Risk: drift between the two approaches, duplicated logic (wallet connect, navigation, selectors) and mismatched configuration defaults.

### D) Design/Consistency Issues (Refactor Footguns)

1) Duplicate selector sources

- Where:
  - `src/browser/dom/selectors.py` contains many selector lists and helper functions.
  - `src/browser/bridge.py` also embeds its own `SelectorStrategy` with overlapping patterns/selectors.
- Risk: selectors diverge over time; bug fixes land in one path but not the other.
- Recommendation: centralize selectors in one module and have both Bridge and Executor consume it.

2) Mixing `print()` and `logging`

- Where: `src/browser/automation.py`, `src/browser/cdp/launcher.py` use `print()`.
- Impact: noisy output in UI environments; harder to route logs; inconsistent verbosity controls.

## Strengths / Improvements Observed

- `BrowserBridge` uses a queue-driven async loop and clear timeouts (`src/browser/bridge.py`) to avoid UI blocking.
- Selector robustness is high (CSS + exact + starts-with + class patterns) with explicit mitigation for `X` vs `X2` (`src/browser/bridge.py`, `src/browser/dom/selectors.py`).
- `BrowserExecutor` wraps many operations in `asyncio.wait_for` to avoid deadlocks (`src/browser/executor.py`).
- CDP lifecycle code is present and reasonably defensive (port checks, profile directories, extension injection verification) (`src/browser/manager.py`).

## Suggested Next Steps (Highest ROI)

1) Fix event forwarding shape for `Events.WS_RAW_EVENT` in `src/browser/bridge.py` so UI debug tooling works.
2) Make `browser/automation.py` timeout handling correct and honor the `timeout` argument; catch Playwright’s `TimeoutError` consistently.
3) Remove `sys.path` mutation from `BrowserBridge._do_connect()` and fix imports structurally.
4) Replace float-based increment planning with `Decimal`/integer math in `BrowserExecutor._build_amount_incrementally_in_browser()`.
5) Decide whether `src/browser/cdp/launcher.py` is still required; if deprecated, isolate it and ensure UI never calls it accidentally.

## Appendix

### Commands run

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(find src/browser -type f -name "*.py")`
- `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_sources/test_cdp_websocket_interceptor.py`
