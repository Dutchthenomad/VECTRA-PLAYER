# Explorer System

Status: in_review (Section 5)
Class: canonical
Last updated: 2026-02-12
Owner: Systems Review
Depends on: `../../01-architecture/CONTRACTS/FOUNDATION_API.md`, `../../03-strategy-and-math/OPTIMIZATION/README.md`
Replaces: explorer system docs and handlers in source corpus

## Purpose

Define explorer service/BFF behavior and UI integration points for analysis workflows.

## Scope

1. strategy data queries,
2. bankroll and Monte Carlo run orchestration,
3. async job status model.

## Source Inputs

1. `system-extracts/02-explorer-ui-and-api.md`
2. `Statistical Opt/EXPLORER-TAB/*.md`
3. `Statistical Opt/code-examples/*.py`

## Canonical Decisions

1. Explorer UI consumes unified BFF envelopes only.
2. Long-running simulations run async with job tracking.
3. Explorer does not own ingestion or live execution paths.
