# Survival Model

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `BAYESIAN_RUG_SIGNAL.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: survival-analysis sections in source docs

## Purpose

Define canonical survival-analysis baseline for rug timing probability estimation.

## Scope

1. Survival and hazard definitions.
2. Conditional window probability for sidebet horizon.
3. Output contract for downstream models.

## Source Inputs

1. `PROBABILISTIC_REASONING.md`
2. `Statistical Opt/STATISTICAL-OPTIMIZATION/17-SURVIVAL-ANALYSIS.md`
3. `risk_management/README.md`

## Canonical Decisions

### 1) Core Definitions

1. `S(t) = P(T > t)`
2. `h(t) = P(T=t | T>=t)` (discrete tick approximation)
3. window probability `P(rug in [t, t+w] | survived to t)` where `w = SIDEBET_WINDOW_TICKS`

### 2) Baseline Estimation

1. Use empirical duration data grouped by game/round.
2. Apply smoothing where sparse tails produce unstable hazard estimates.
3. Preserve sample-size visibility for every reported probability band.

### 3) Output Contract

At minimum, model output includes:

- `tick`
- `window_ticks`
- `p_rug_window`
- `baseline_confidence` (or sample-size proxy)

### 4) Breakeven Comparison Rule

Probability edge comparisons must explicitly state which breakeven model is used (`programmatic` vs `comprehensive`).

## Open Questions

1. Should survival baseline include regime-conditioned curves in v1, or remain unconditional baseline plus Bayesian adjustment?
