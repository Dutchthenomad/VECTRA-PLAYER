# Src Entry-Point Audit (`src/config.py`, `src/main.py`)

Date: 2025-12-22

## Scope

Audited:

- `src/config.py`
- `src/main.py`

This report focuses on entry-point / bootstrap correctness, configuration safety, portability, and lifecycle management. Findings may reference downstream modules where required to explain impact.

## Methodology

- Manual review for API consistency, portability, error handling, configuration serialization, and shutdown/lifecycle.
- Syntax check: `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile src/config.py src/main.py` (passed).

## Executive Summary

The overall structure is reasonable for a post-refactor bootstrap (explicit runtime init path, config validation, central logger setup, and a single `Application` orchestrator). The highest risk issues are:

- **Import path manipulation in `main.py`** can cause module shadowing / unpredictable imports depending on where the app is launched from.
- **`Config.BROWSER["cdp_port"]` can crash on invalid env** (unvalidated `int()` conversion at import time).
- **Shutdown uses `signal.SIGALRM`/`signal.alarm`**, which is **not portable to Windows** and will also fail if `shutdown()` is called from a non-main thread.
- **Config save/load type drift**: settings persisted as JSON do not round-trip several important Python types (e.g., `frozenset`), and `save_to_file()` omits a `files` section despite `load_from_file()` supporting one.

## Findings (Prioritized)

### A) Confirmed Bugs / Likely Runtime Errors

1) Import-time crash on invalid `CDP_PORT`

- Where: `src/config.py` (`Config.BROWSER["cdp_port"] = int(os.getenv("CDP_PORT", "9222"))`).
- What: If `CDP_PORT` is set to a non-integer value, importing `config` raises `ValueError` immediately.
- Impact: application fails before logging/UI are initialized (harder to diagnose).
- Recommendation: parse via `_safe_int_env("CDP_PORT", 9222, 1, 65535)` (or similar) rather than `int(...)`.

2) `Config.save_to_file()` does not persist `files` even though `load_from_file()` supports it

- Where:
  - Load supports sections including `"files"`: `src/config.py` (`load_from_file()` loops `["financial", "game_rules", "bot", "files"]`).
  - Save omits `"files"`: `src/config.py` (`save_to_file()` builds `config_dict` without a `files` section).
- Impact: settings intended to be persisted for file paths (recordings/log/config dirs) won’t be written, and any user-provided `files` overrides may appear to “not stick” across restarts.
- Recommendation: either add `files` to `save_to_file()` or remove `files` from load/merge to avoid misleading behavior.

3) Windows portability bug: shutdown uses `signal.SIGALRM` / `signal.alarm`

- Where: `src/main.py:shutdown()`.
- What: `signal.SIGALRM` and `signal.alarm()` are Unix-only; on Windows this raises `AttributeError`.
- Impact: shutdown path can crash on Windows; even on Unix it requires `shutdown()` be called on the main thread.
- Recommendation: guard with `hasattr(signal, "SIGALRM")` and/or use a thread-based timeout that does not require signals.

### B) Lifecycle / Concurrency Risks

1) `shutdown()` is not thread-safe due to signal usage

- Where: `src/main.py:shutdown()`.
- What: `signal.signal(...)` can only be called from the main thread in CPython. If any background thread calls `Application.shutdown()` (directly or via an event callback), shutdown can raise `ValueError` and skip cleanup.
- Recommendation: ensure shutdown is always marshaled onto the Tk main thread (`root.after(0, ...)`) or remove signal usage in favor of a safer timeout mechanism.

2) Re-entrancy / multi-call shutdown behavior is undefined

- Where: `src/main.py`.
- What:
  - UI close handler directly invokes `shutdown()` (`WM_DELETE_WINDOW` binding).
  - `main()` also calls `app.shutdown()` in its `finally`.
  - `shutdown()` ends with `sys.exit(0)`, which can abruptly terminate the process from inside UI callbacks and can make outer cleanup code unreachable.
- Impact: difficult-to-reason-about teardown ordering; increased chance of double-stop / double-destroy errors (partially mitigated by `try/except`).
- Recommendation: make `shutdown()` idempotent (one-way state flag), avoid `sys.exit()` deep in the object, and let `main()` own process exit.

### C) Import / Packaging / Environment Conflicts

1) `sys.path` injection can cause module shadowing and inconsistent imports

- Where: `src/main.py` (inserting the repo parent dir at index 0).
- What: When running `python src/main.py` from the repo root, the inserted parent directory becomes the first import location. If that directory contains modules that overlap names in `src/` (e.g. another `config.py`, `services/`, `ui/`), imports can silently resolve to the wrong module.
- Impact: non-deterministic behavior across environments, especially on developer machines with multiple similar repos/layouts.
- Recommendation: avoid runtime `sys.path` modifications; prefer packaging (`python -m ...`), or explicitly insert the `src/` directory (not the repo parent), or use absolute package imports with a proper package root.

2) Redundant / inconsistent config access patterns

- Where: `src/main.py` uses both `self.config` and the module-global `config` instance.
- Impact: increases cognitive load and makes it easy to accidentally use an uninitialized config instance in future refactors.
- Recommendation: consistently use `self.config` once set, and only use the module-global `config` during early bootstrap.

### D) Configuration Semantics / Serialization / Validation Gaps

1) JSON round-trip does not preserve several types (and can corrupt settings)

- Where: `src/config.py:_serialize_dict()` / `_deserialize_dict()` and `save_to_file(default=str)`.
- What:
  - `frozenset` (e.g. `GAME_RULES["blocked_phases"]`) is not serialized with type tags; it becomes a string via `default=str`.
  - Other non-JSON types will degrade similarly (e.g. tuples/sets).
  - Load does not restore these values, so a user override can become the wrong type.
- Impact: subtle runtime bugs if code expects the original type (e.g. membership checks against a `frozenset`).
- Recommendation: either (a) enforce JSON-only types for persisted settings, or (b) extend tagged serialization to cover sets/frozensets and validate loaded types.

2) Class-level dicts are mutable and shared across instances

- Where: `src/config.py` (`FINANCIAL`, `GAME_RULES`, `UI`, etc.).
- What: they act as constants but are mutable dicts; any runtime mutation affects all instances and can leak between tests/sessions.
- Impact: stateful bugs that are hard to reproduce; potential test-order dependence.
- Recommendation: treat them as immutable (copy on read, or convert to frozen dataclasses / MappingProxyType), or ensure no code mutates them at runtime.

3) Validation coverage is uneven across env-derived fields

- Where: `src/config.py`.
- What:
  - Live feed env vars are bounds-checked (`_safe_int_env`).
  - Browser `cdp_port` is not bounds-checked and can crash at import.
  - Several directories default into `src/` (e.g. `recordings_dir`), which can be surprising and may not be writable in packaged installs.
- Recommendation: apply the same safe parsing + bounds validation across all env-derived numeric fields and document default storage locations.

## Suggested Fix Order (High Leverage)

1) Make `CDP_PORT` parsing safe and validate port bounds (`src/config.py`).
2) Remove/limit `sys.path` injection in `src/main.py` (or at least avoid inserting the repo parent at index 0).
3) Make shutdown portable and thread-safe (remove SIGALRM dependence, marshal shutdown to main thread, ensure idempotency).
4) Fix config persistence mismatch (`files` section) and prevent type drift in saved settings.
