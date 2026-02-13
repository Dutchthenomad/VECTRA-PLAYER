# Modes and Execution Model

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `../00-governance/GLOSSARY.md`, `EVENT_MODEL.md`, `SERVICE_BOUNDARIES.md`
Replaces: inconsistent mode naming in source docs

## Purpose

Define canonical runtime modes and the execution constraints for each mode.

## Scope

Applies to architecture docs, APIs, UI labels, and operations runbooks.

## Source Inputs

1. `PROCESS_FLOWCHARTS.md`
2. `system-extracts/03-backtest-engine.md`
3. `system-extracts/06-live-simulator-paper-trading.md`
4. `system-extracts/07-offline-v1-simulator-artifact.md`
5. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
6. `Statistical Opt/03-EVENT-SYSTEM.md`

## Canonical Decisions

### 1) Canonical Modes

1. `replay`
2. `backtest`
3. `live-simulator`
4. `live-execution`
5. `paper-trading` (execution policy, not standalone source mode)

### 2) Mode Definitions

1. `replay`: visual/diagnostic tick playback from recorded data.
2. `backtest`: deterministic strategy simulation over historical datasets.
3. `live-simulator`: simulation driven by live feed, with simulated wallet/fills.
4. `live-execution`: real trading actions sent to execution bridge/provider.
5. `paper-trading`: no real orders; can be applied within backtest or live-simulator contexts.

### 3) Allowed Combinations

1. `backtest + paper-trading` allowed.
2. `live-simulator + paper-trading` allowed.
3. `live-execution + paper-trading` not allowed.
4. `replay + live-execution` not allowed.

### 4) Service Isolation Rule

1. `live-simulator` service must not execute real orders.
2. `live-execution` path must be routed through execution bridge service.
3. Any toggle that enables real execution inside simulator process is non-canonical.

### 5) Determinism Expectations

1. `backtest` should be deterministic for same dataset + config + seed.
2. `replay` should preserve source event order and timestamps (or explicit normalized timing mode).
3. `live-simulator` is non-deterministic across runs unless feed snapshots are captured.

### 6) UI Labeling Rule

UI must display explicit mode badge with canonical names; never generic `simulator` label without qualifier.

### 7) Transition Semantics

Recommended lifecycle:

1. research in `replay`,
2. strategy validation in `backtest`,
3. operational rehearsal in `live-simulator`,
4. controlled rollout in `live-execution`.

## Open Questions

1. Should `replay` remain independent or be folded into backtest controls as a submode?
2. Do we require explicit operator confirmation gates to move from `live-simulator` to `live-execution`?
