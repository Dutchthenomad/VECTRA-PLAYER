# Project Status

Last updated: 2025-12-24

## Canonical Status Sources

- This file is the source of truth for current status.
- The active roadmap is in `docs/ROADMAP.md`.
- Superseded status/audit/plan documents are archived in
  `sandbox/DEVELOPMENT DEPRECATIONS/`.

## Current Phase

Phase 12D -> 12E transition. The system is functional with EventStore and
LiveStateProvider integrated, but remaining crash fixes, thread-safety work,
and legacy cleanup are in progress.

## Now (Highest Priority)

- Phase 1: Remaining P0 crash fixes across core, UI, browser, and sources.
- Phase 2: Thread-safety and data-integrity stabilization.

## Next

- Phase 3: GUI audit remediation and removal of legacy recorder paths.
- Phase 4: Socket cleanup and live/replay state separation.
- Phase 5: Quality sweep, tests, and coverage stabilization.

## Archive Policy

If a status, audit, plan, or summary doc is replaced by this file or
`docs/ROADMAP.md`, it should be moved to
`sandbox/DEVELOPMENT DEPRECATIONS/` rather than deleted.
