# Monte Carlo

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `STRATEGY_PROFILE_GENERATION.md`, `../RISK/RISK_METRICS.md`
Replaces: monte-carlo docs in source corpus

## Purpose

Define canonical Monte Carlo simulation methodology for strategy robustness analysis.

## Scope

1. Input assumptions and parameterization.
2. Simulation run contract.
3. Output metric and distribution schema.

## Source Inputs

1. `Statistical Opt/STATISTICAL-OPTIMIZATION/14-MONTE-CARLO-SIMULATOR.md`
2. `Statistical Opt/EXPLORER-TAB/10-MONTE-CARLO-COMPARISON.md`
3. `risk_management/02_drawdown_analysis.py`
4. `system-extracts/05-monte-carlo-comparison.md`

## Canonical Decisions

### 1) Simulation Metadata Requirement

Every run records:

- seed
- iteration count
- game count
- assumptions (`p_win`, payout semantics, sizing profile)
- dataset/version

### 2) Core Outputs

1. final bankroll distribution
2. drawdown distribution
3. ruin probability
4. risk-adjusted performance summary

### 3) Comparison Rule

Strategy comparisons must share identical simulation assumptions unless explicitly labeled as sensitivity analysis.

## Open Questions

1. Should we standardize fixed seed sets for baseline comparability across releases?
