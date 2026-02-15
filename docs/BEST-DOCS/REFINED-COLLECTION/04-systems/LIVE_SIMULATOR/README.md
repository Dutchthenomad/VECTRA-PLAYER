# Live Simulator System

Status: in_review (Section 5)
Class: canonical
Last updated: 2026-02-12
Owner: Systems Review
Depends on: `../../01-architecture/MODES_AND_EXECUTION_MODEL.md`, `../../01-architecture/EVENT_MODEL.md`
Replaces: live simulator/paper trading docs in source corpus

## Purpose

Define live-feed paper-trading simulator system behavior.

## Scope

1. live feed consumption,
2. sessioned simulation state,
3. output stream contracts,
4. guardrails against real execution coupling.

## Source Inputs

1. `system-extracts/06-live-simulator-paper-trading.md`
2. `Statistical Opt/BACKTEST-TAB/12-LIVE-TRADING-MODE.md`
3. `PROCESS_FLOWCHARTS.md`

## Canonical Decisions

1. Live simulator is feed-driven but execution-simulated only.
2. Real execution path must remain externalized in execution bridge service.
3. Session outputs follow canonical event envelope/schema.
