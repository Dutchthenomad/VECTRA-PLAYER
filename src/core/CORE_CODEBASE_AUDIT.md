# Core Codebase Audit (`src/core`)

Date: 2025-12-22

## Scope

Audited Python modules in `src/core/`:

- `__init__.py`
- `demo_recorder.py`
- `game_queue.py`
- `game_state.py`
- `live_ring_buffer.py`
- `recorder_sink.py`
- `replay_engine.py`
- `replay_playback_controller.py`
- `replay_source.py`
- `session_state.py`
- `trade_manager.py`
- `validators.py`

Out of scope: other packages (`src/services`, `src/models`, UI) except where needed to reason about behavior.

## Methodology

- Manual review focused on correctness, concurrency/threading, I/O durability, and API consistency.
- Pattern scans for exception swallowing, threading/locks, file I/O, and conflict markers.
- Syntax check: `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile src/core/*.py`
- Unit test sweep (core): `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_core`
  - Result: **224 passed** (2 warnings reported by pytest, not expanded in `-q` output).

## Executive Summary

The folder is generally well-structured after refactoring (separation of playback controller, bounded buffers, atomic session writes, recorder safety checks). The unit tests for `tests/test_core/` currently pass.

However, there are several **high-risk correctness and concurrency issues** that can surface in production even if tests pass, notably:

- **Confirmed runtime bug**: `TradeManager` treats `GameState.sidebet` as an object with attributes, but `GameState` stores sidebets as dicts.
- **Thread lifecycle hazards** in `PlaybackController` that can lead to duplicate playback threads or deadlocks.
- **Observer/event dispatch under lock** patterns in `GameState` (and event publishing under engine locks) that are safe in trivial handlers but can deadlock when handlers interact with UI / other locks.
- **Demo recording durability gaps**: confirmation updates can remain only in-memory for long periods and can be lost on crash.

## Findings (Prioritized)

### A) Confirmed Bugs / Likely Runtime Errors

1) `TradeManager` sidebet type mismatch (dict vs object)

- Where: `src/core/trade_manager.py:296` onward.
- What: `sidebet = self.state.get("sidebet")` is assumed to have attributes (`sidebet.placed_tick`, `sidebet.amount`), but `GameState.place_sidebet()` stores a dict:
  - `src/core/game_state.py:632-650` stores `{"amount": ..., "placed_tick": ..., ...}`.
- Impact: `AttributeError: 'dict' object has no attribute 'placed_tick'` in:
  - `TradeManager.check_and_handle_rug()` (`src/core/trade_manager.py:278-315`)
  - `TradeManager.check_sidebet_expiry()` (`src/core/trade_manager.py:316-339`)
- Why tests didn’t catch it: current core tests don’t exercise these rug/expiry methods.

2) `GameState.get_current_tick()` reports “rugged” from `rug_detected`, not from `rugged`

- Where: `src/core/game_state.py:163-184` (specifically `src/core/game_state.py:175`).
- What: It creates a `GameTick` with `"rugged": self._state.get("rug_detected", False)`.
- Impact: any logic consuming `GameState.get_current_tick()` can see `tick.rugged=False` even when the current tick/state is actually rugged (`self._state["rugged"] == True`), which can break validation/logic that keys on `tick.rugged`.

3) `PlaybackController.cleanup()` can deadlock by joining its own thread

- Where: `src/core/replay_playback_controller.py:273-284`.
- What: `cleanup()` unconditionally joins `self.playback_thread` if alive. If `cleanup()` is invoked from the playback thread (directly or indirectly), `thread.join()` will deadlock.
- Note: `pause()` has a self-join guard (`src/core/replay_playback_controller.py:94-101`), but `cleanup()` does not.

### B) Concurrency / Race Condition Risks

1) Playback thread wake/join behavior can leave “zombie” playback threads

- Where:
  - `PlaybackController.pause()` (`src/core/replay_playback_controller.py:86-104`)
  - `PlaybackController._playback_loop()` (`src/core/replay_playback_controller.py:238-268`)
  - `PlaybackController.play()` (`src/core/replay_playback_controller.py:63-85`)
- What:
  - `pause()` sets `is_playing = False` but does **not** set `_stop_event`, so if the thread is blocked in `_stop_event.wait(timeout=delay)`, it may not exit until the timeout elapses.
  - `pause()` joins with a fixed `timeout=2.0`. At low speeds the delay can be up to `2.5s` (`delay = 0.25 / 0.1`), so pause can return with the thread still alive.
  - `play()` only checks `is_playing`, not whether an existing `playback_thread` is alive; it can start a second playback thread if the first is still winding down.
- Impact: intermittent double-stepping, unexpected state updates, and difficult-to-reproduce UI bugs.

2) `GameState` observer callbacks can effectively run while the state lock is held

- Where:
  - Many mutators call `_emit()` while holding `self._lock`, e.g. `src/core/game_state.py:413-457`, `src/core/game_state.py:505-614`, `src/core/game_state.py:652-678`.
  - `_emit()` itself releases the lock before calling callbacks (`src/core/game_state.py:829-841`), but it is typically invoked from within an outer `with self._lock:` block.
- Why this matters:
  - Because the lock is an `RLock`, callbacks executed on the same thread can re-enter `GameState` safely.
  - But callbacks that interact with other subsystems (Tkinter/UI thread handoff, event bus subscribers, engine locks, or blocking calls that require another thread to read state) can deadlock or cause priority inversions.
- Recommendation: collect events and dispatch after releasing the outer lock, or centralize event dispatch via an async queue to a single “state event thread” / UI thread.

3) `ReplayEngine` publishes events and runs callbacks from multiple threads

- Where:
  - Playback thread calls `_display_tick_direct()` via `display_tick()` / `step_forward()` (controller thread) and publishes `Events.GAME_TICK` (`src/core/replay_engine.py:509-568`).
  - Live feed pushes can also call `_display_tick_direct()` (`src/core/replay_engine.py:412-431`).
- Risk: if `event_bus.publish()` dispatches subscribers inline (typical pub/sub), then subscribers may run on:
  - playback background thread, or
  - whatever thread calls `push_tick()`.
  If those subscribers touch Tkinter widgets directly, this is unsafe unless the event bus explicitly marshals to the UI thread.
- Note: this is a cross-module concern; confirm `src/services/event_bus` threading semantics.

4) `RecorderSink._safe_file_operation()` can re-enter `stop_recording()` during stop/flush

- Where: `src/core/recorder_sink.py:109-124`.
- What:
  - On repeated `OSError`, `_safe_file_operation` calls `self.stop_recording()` while already in a recording workflow.
  - If the error occurs while `stop_recording()` itself is flushing inside `_safe_file_operation`, this can recurse.
- Impact: risk of deep recursion/stack growth or inconsistent teardown in pathological disk-error scenarios.

### C) Data Integrity / File I/O Durability

1) `DemoRecorderSink.record_confirmation()` does not flush confirmed actions

- Where: `src/core/demo_recorder.py:395-435`.
- What:
  - Confirmation data is applied only to the in-memory `_buffer`.
  - Confirmed actions are written to disk only when `_flush()` is triggered by later button presses or at game end.
- Impact: if the app crashes or is killed after confirmations but before the next flush condition, confirmation timing/metadata can be lost.
- Possible mitigations:
  - call `_flush()` opportunistically after applying confirmation (when the confirmed action is no longer pending), or
  - add a time-based flush like `RecorderSink` (`src/core/recorder_sink.py:319-323`).

2) `DemoRecorderSink` filename uses raw `game_id`

- Where: `src/core/demo_recorder.py:245-248`.
- Risk:
  - If `game_id` contains path separators or `..`, it can create unintended paths or invalid filenames (depending on platform/filesystem).
  - Even if `game_id` is “trusted” today, this is a hard-to-debug footgun.
- Recommendation: sanitize to a safe filename component (allowlist `[a-zA-Z0-9._-]`, replace others with `_`) and optionally truncate.

3) `FileDirectorySource` path resolution allows directory traversal

- Where: `src/core/replay_source.py:177-186`.
- What: `_resolve_path()` returns `self.directory / identifier` for non-absolute identifiers, without preventing `../`.
- Impact: a caller could read arbitrary files relative to the recordings directory if identifier comes from user input.
- Recommendation: resolve and verify `resolved_path.is_relative_to(self.directory.resolve())` (Python 3.9+ via `.resolve()` + manual check) before allowing the read.

4) `RecorderSink.total_bytes_written` counts characters, not bytes

- Where: `src/core/recorder_sink.py:363-367`.
- What: `file_handle.write()` returns character count for text files, not bytes.
- Impact: metrics may be misleading (not a correctness issue for recording itself).

5) `SessionState` atomic write is good; corruption handling could be improved

- Good: atomic replace (`src/core/session_state.py:121-134`) prevents partial writes.
- Potential improvement: on `JSONDecodeError` in `load()` (`src/core/session_state.py:93-99`), consider backing up the corrupt file and rewriting defaults to restore persistence.

### D) Consistency / Design Conflicts (Refactor Footguns)

1) Dual rug flags (`rugged` vs `rug_detected`)

- Where: `src/core/game_state.py:119-123`, `src/core/replay_engine.py:559-562`, `src/core/replay_engine.py:529-541`.
- Current usage:
  - `rugged`: appears to mirror tick.rugged (server/game truth).
  - `rug_detected`: appears to be “local handled rug event already”.
- Risk: easy to mix up (as seen in `get_current_tick()`), leading to subtle logic bugs.
- Recommendation: rename for clarity (e.g. `is_rugged` vs `rug_event_emitted`) or consolidate into a single source of truth + derived flag.

2) Amount/price semantics are easy to misinterpret

- Models describe `price` as a multiplier (`src/models/game_tick.py`, `src/models/position.py`), but core logic treats a position as if:
  - cost to open is `amount * entry_price` (`src/core/game_state.py:564-565`),
  - proceeds are `amount * exit_price` (`src/core/game_state.py:585-599`).
- This may be intentional, but it conflicts with the “amount invested” phrasing in `src/models/position.py` and with validator checks that compare `amount` directly to `balance` (`src/core/validators.py:10-73`).
- Recommendation: tighten naming/documentation:
  - if `amount` is “exposure units”, rename it (`units`, `qty`) and validate affordability using `amount * price`;
  - if `amount` is “SOL invested”, update open/close math to match that model.

3) Heavy reliance on broad exception handling

- Notable locations:
  - `src/core/demo_recorder.py:117-121`, `src/core/recorder_sink.py:102-107`, destructors in both recorders.
- Tradeoff: avoids crashing during shutdown, but can hide real operational failures (especially during normal runtime).
- Recommendation: restrict broad `except Exception` to shutdown paths; otherwise log with `exc_info=True` and include contextual identifiers (game_id, file path).

## Strengths / Improvements Observed

- Memory bounding:
  - `LiveRingBuffer` prevents unbounded tick growth (`src/core/live_ring_buffer.py`).
  - `GameState` uses bounded `deque` history/logs (`src/core/game_state.py:84-90`).
- Recording durability improvements:
  - `RecorderSink` validates file handle (`src/core/recorder_sink.py:324-342`) and fsyncs on flush (`src/core/recorder_sink.py:368-369`).
- Clear separation of responsibilities:
  - playback logic extracted to `PlaybackController`.
  - replay source abstraction via `ReplaySource`.

## Suggested Next Steps (Highest ROI)

1) Fix `TradeManager` sidebet access to handle dict storage (or change `GameState` to store a `SideBet` object consistently).
2) Harden `PlaybackController` lifecycle:
   - wake the loop on pause (`_stop_event.set()` + clear on play),
   - prevent starting a new thread if the previous one is still alive,
   - add self-join guard in `cleanup()`.
3) Correct `GameState.get_current_tick()` to map `rugged` from `self._state["rugged"]`.
4) Sanitize demo recording filenames and tighten replay source path resolution.
5) Decide and document the canonical meaning of `amount` vs `price` across `GameTick`, `Position`, `validators`, and `GameState`.

## Appendix

### Commands run

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile src/core/*.py`
- `cd src && PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_core`
