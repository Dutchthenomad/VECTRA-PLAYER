# Roadmap

Last updated: 2025-12-24

This roadmap unifies remaining goals and cleanup work. It is the canonical
reference for planning and execution.

## Phase 1: Remaining P0 Crash Fixes (Immediate)

Scope:
- Core: PlaybackController cleanup self-join deadlock.
- Core: PlaybackController duplicate thread/zombie playback loop.
- UI: BotManager uses tick.active instead of game_active.
- UI: Toast bootstyle misuse.
- UI: LiveFeedController calls nonexistent set_seed_data().
- UI: BrowserConnectionDialog constructor missing required arg.
- UI: RecordingController calls missing toast.show().
- Browser: WS_RAW_EVENT double-wrapped publish.
- Browser: Playwright timeout exception type mismatch.
- Browser: Runtime sys.path mutation in BrowserBridge.
- Sources: socketio_parser unreachable duplicate code.
- Sources: PriceHistoryHandler double-finalization.

Acceptance checks:
- Repro steps for each crash no longer throw.
- `cd src && pytest tests/ -v` passes or failures are triaged with notes.

## Phase 2: Thread-Safety and Data Integrity (Stabilization)

Scope:
- EventSourceManager publishes while holding lock.
- CDPBrowserManager stderr pipe can block Chrome.
- Live feed race conditions and state reconciliation gaps.

Acceptance checks:
- No Tk thread violations under live feed stress.
- Long-running automation sessions do not stall due to blocked pipes.

## Phase 3: GUI Audit Remediation (Phase 12E Prep)

Scope:
- Move UI subprocess work off the UI thread.
- Remove legacy recorder mixins and menu items.
- Standardize EventBus -> EventStore capture path.

Acceptance checks:
- UI remains responsive during capture analysis.
- No legacy recorder codepaths reachable in live mode.

Execution note:
- This phase must be completed by a different model (not this agent).

## Phase 4: Socket Cleanup and Live/Replay Separation

Scope:
- Button state control based on LiveStateProvider.
- Live validation uses server balance when connected.
- GameState becomes replay-only; live mode read-only or unused.

Acceptance checks:
- Live mode buttons reflect server state correctly.
- No GameState mutation in live mode without warning.

## Phase 5: Quality Sweep

Scope:
- Resolve remaining P2/P3 audit items.
- Add tests for fixed crash paths and regressions.

Acceptance checks:
- `ruff check .` clean.
- Coverage does not regress.

## Cleanup Track (Continuous)

- Archive superseded status/audit/plan docs to
  `sandbox/DEVELOPMENT DEPRECATIONS/`.
- Avoid new ad-hoc summary docs; update this roadmap instead.
- When deprecating a doc, add a short note indicating the archive location.
