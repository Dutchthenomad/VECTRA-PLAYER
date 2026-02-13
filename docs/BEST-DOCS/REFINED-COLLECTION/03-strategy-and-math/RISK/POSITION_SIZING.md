# Position Sizing

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `DRAWDOWN_CONTROL.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: sizing sections in risk and statistical optimization docs

## Purpose

Define canonical position sizing model and interfaces.

## Scope

1. Kelly-family sizing.
2. Fractional and bounded sizing controls.
3. Runtime sizing inputs and outputs.

## Source Inputs

1. `risk_management/README.md`
2. `risk_management/01_position_sizing.py`
3. `Statistical Opt/STATISTICAL-OPTIMIZATION/15-KELLY-CRITERION.md`
4. `Statistical Opt/BACKTEST-TAB/13-POSITION-SIZING.md`

## Canonical Decisions

### 1) Baseline Formula

Use Kelly-style sizing with explicit payout semantics and bounded fractional variants.

### 2) Required Inputs

- `p_win`
- payout semantics (`r_total` and/or `r_profit`)
- bankroll
- risk profile/fraction

### 3) Required Guards

1. no bet when estimated edge is non-positive under selected semantics,
2. hard cap on fraction per trade,
3. mode-aware cap reductions under stressed states.

### 4) Output Contract

- `fraction`
- `bet_size`
- `edge_model` label
- guard decisions (clamped/rejected)

## Open Questions

1. Should volatility-adjusted Kelly be core default or optional strategy plugin?
