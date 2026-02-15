# Backtest System

Status: in_review (Section 5)
Class: canonical
Last updated: 2026-02-12
Owner: Systems Review
Depends on: `../../01-architecture/MODES_AND_EXECUTION_MODEL.md`, `../../03-strategy-and-math/RISK/README.md`
Replaces: backtest docs in source corpus

## Purpose

Define deterministic historical simulation service behavior and control APIs.

## Scope

1. session lifecycle,
2. tick/control commands,
3. strategy evaluation outputs,
4. reproducibility metadata.

## Source Inputs

1. `system-extracts/03-backtest-engine.md`
2. `Statistical Opt/BACKTEST-TAB/*.md`
3. `PROCESS_FLOWCHARTS.md` (replay/backtest flow)

## Canonical Decisions

1. Backtest runs are deterministic for same data/config/seed.
2. Session state should be externalized for reliability.
3. Backtest mode cannot execute real orders.
