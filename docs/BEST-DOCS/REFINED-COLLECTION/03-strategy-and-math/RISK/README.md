# Risk

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `POSITION_SIZING.md`, `DRAWDOWN_CONTROL.md`, `RISK_METRICS.md`
Replaces: risk-management docs and notebook notes

## Purpose

Define canonical risk controls and metrics for sidebet/strategy systems.

## Scope

1. Position sizing logic.
2. Drawdown and state controls.
3. Risk-adjusted metrics and evaluation thresholds.

## Canonical Decisions

1. Sizing, drawdown, and metrics are separate modules with explicit interfaces.
2. Risk controls are required preconditions to any live-execution rollout.
3. Metrics interpretations must document confidence/sample-size context.
