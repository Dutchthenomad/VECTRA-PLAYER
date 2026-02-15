# Systems

Status: in_review (Section 5)
Class: canonical
Last updated: 2026-02-12
Owner: Systems Review
Depends on: `../01-architecture/README.md`, `../03-strategy-and-math/README.md`
Replaces: system implementation guidance spread across source docs

## Purpose

Define per-system implementation-facing docs aligned to architecture and strategy canon.

## Scope

1. Foundation system.
2. Explorer system.
3. Backtest system.
4. Live simulator system.
5. ML pipeline system.

## Source Inputs

1. `system-extracts/*.md`
2. `Statistical Opt/BACKTEST-TAB/*.md`
3. `Statistical Opt/EXPLORER-TAB/*.md`
4. `Statistical Opt/code-examples/*.py`
5. `2025-12-28-pipeline-d-training-data-implementation.md`

## Canonical Decisions

1. Systems docs define module behavior and interfaces, not business policy.
2. All systems must point to architecture contracts for API/event schema details.
3. Each subsystem doc must include migration lineage from source inputs.
