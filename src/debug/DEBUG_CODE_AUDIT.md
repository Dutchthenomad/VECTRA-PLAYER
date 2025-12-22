# Debug Code Audit Report (`src/debug/`)

Date: 2025-12-22
Scope: All source files under `src/debug/`.
Method: Manual static review + `python3 -m compileall -q src/debug` (syntax check).

## Executive Summary

`src/debug/` is small and focused: it exposes a single developer tool (`RawCaptureRecorder`) for capturing raw Socket.IO events into JSONL for protocol discovery. The implementation is mostly robust for a debug/diagnostic utility (lock-protected file writes, JSON-safe serialization, non-blocking connection/disconnect paths).

The main concerns are around:

- callback/thread lifecycle correctness (callbacks invoked from background threads without error isolation; asynchronous callback timing can be flaky for consumers/tests),
- state cleanup semantics (some fields are left populated after stop),
- and import ergonomics (`debug/__init__.py` uses a top-level import style that assumes `src/` is on `PYTHONPATH`).

No syntax errors were found.

## Inventory (Files Reviewed)

- `src/debug/__init__.py`
- `src/debug/raw_capture_recorder.py`

Non-runtime artifacts present in-tree:
- `src/debug/__pycache__/...` (bytecode cache directory)

## High Priority Findings (Fix Soon)

### 1) Callbacks may execute on background threads without safety guards

**Why this matters**
- `on_capture_stopped` is invoked from the `disconnect_async` background thread in `stop_capture()`, without a `try/except`.
- If the callback raises, the exception is unhandled in that thread and can be noisy and/or skip subsequent cleanup steps in the thread.
- For UI integration (Tkinter), calling UI code from a background thread is unsafe; callbacks should be dispatched onto the UI thread (e.g., via `TkDispatcher`) or documented as “background-thread callbacks”.

**Where**
- `src/debug/raw_capture_recorder.py` (`stop_capture()` → `disconnect_async()` → `on_capture_stopped`)

**Recommended remediation**
- Wrap `on_capture_stopped(...)` in `try/except` like `_record_event()` already does for `on_event_captured`.
- Consider offering a “dispatcher” hook or requiring callbacks to be thread-safe.

### 2) `stop_capture()` callback timing is asynchronous and can be flaky for consumers

**Why this matters**
- `stop_capture()` returns immediately after starting `disconnect_thread`; `on_capture_stopped` is called later.
- Consumers that expect “stop means stopped” semantics may read status or proceed assuming callbacks already fired.
- The test suite currently asserts callback invocation immediately after `stop_capture()`; this can be timing-sensitive depending on scheduler/CI load.

**Where**
- `src/debug/raw_capture_recorder.py` (`stop_capture`)

**Recommended remediation**
- Call `on_capture_stopped` synchronously (after closing the file) and keep only the socket disconnect in the background thread; or provide an option to block until the callback has fired (join with timeout).

## Medium Priority Findings (Fix When Practical)

### 3) Cleanup semantics: state is partially retained after stopping

**Why this matters**
- `_cleanup()` sets `is_capturing=False`, closes the file handle, and sets `sio=None`, but leaves fields like `capture_file`, `event_counts`, `sequence_number`, and `start_time` intact.
- This can be intentional (“last capture info”), but it’s not documented and can confuse callers reading `get_status()` after stopping.

**Where**
- `src/debug/raw_capture_recorder.py` (`_cleanup()`, `get_status()`)

**Recommended remediation**
- Either document that `get_status()` returns “last capture stats” even when not capturing, or split into `get_status()` vs `get_last_summary()`.

### 4) Timestamp timezone consistency

**Why this matters**
- Event timestamps use `datetime.now().isoformat()` (local timezone, naive datetime). Other parts of the codebase increasingly use UTC or timezone-aware timestamps (e.g., CDP interceptor uses UTC).
- Mixing timezone conventions makes later correlation harder.

**Where**
- `src/debug/raw_capture_recorder.py` (`_record_event`, `start_capture`, `stop_capture`)

**Recommended remediation**
- Prefer timezone-aware UTC timestamps (e.g., `datetime.now(UTC).isoformat()`).

### 5) Optional dependency behavior: capture “starts” even if Socket.IO isn’t installed

**Why this matters**
- If `python-socketio` is missing, `start_capture()` still opens a file and sets `is_capturing=True`, but will never connect or record anything automatically.
- This may be fine for tests, but for real usage it can be surprising.

**Where**
- `src/debug/raw_capture_recorder.py` (`start_capture`)

**Recommended remediation**
- Consider failing fast (return `None` / raise) when dependency is missing, or add an explicit “offline capture mode” message and set `is_capturing=False` unless connected.

### 6) Import style in `debug/__init__.py` assumes top-level package import layout

**Why this matters**
- `from debug.raw_capture_recorder import RawCaptureRecorder` depends on `src/` being on `PYTHONPATH` (or equivalent packaging).
- In more typical package layouts, relative imports are more robust within the package.

**Where**
- `src/debug/__init__.py`

**Recommended remediation**
- Prefer `from .raw_capture_recorder import RawCaptureRecorder` (does not change external imports).

## Suggested Validation Checklist (After Fixes)

- Run tests (repo-standard): `cd src && python3 -m pytest tests/ -v`
- Specifically monitor `src/tests/test_debug/test_raw_capture_recorder.py` for any timing flakiness around `on_capture_stopped`.
