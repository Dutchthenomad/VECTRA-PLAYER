# Position and Sidebet Rules

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `MARKET_MECHANICS.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: sidebet/position rule fragments in source docs

## Purpose

Define canonical rule semantics for positions and sidebets used by strategy and simulation services.

## Scope

1. Entry/exit rule semantics.
2. Sidebet window and payout semantics.
3. Breakeven representations.

## Source Inputs

1. `risk_management/README.md`
2. `PROBABILISTIC_REASONING.md`
3. `Machine Learning/models/sidebet-v1/training_data/README.md`
4. `Statistical Opt/BACKTEST-TAB/13-POSITION-SIZING.md`

## Canonical Decisions

### 1) Sidebet Window Rule

Sidebet win/lose evaluation uses `SIDEBET_WINDOW_TICKS` from constants canon.

### 2) Payout/Breakeven Rule

Both canonical expressions are valid and must be labeled explicitly:

1. Programmatic settlement model (`R_total=5`, breakeven 20%).
2. Comprehensive odds model (`R_profit=5`, `R_total=6`, breakeven 16.67%).

### 3) Rule vs Policy Separation

1. Domain rules define what outcomes mean.
2. Strategy policy defines whether/when to bet.

### 4) Minimum Outcome Fields

A sidebet result record should include:

- `start_tick`
- `window_ticks`
- `r_total`
- `r_profit` (recommended)
- `won`
- `settlement_tick`

## Open Questions

1. Do we canonize a single runtime payout model for APIs while retaining dual analytic semantics in docs?
