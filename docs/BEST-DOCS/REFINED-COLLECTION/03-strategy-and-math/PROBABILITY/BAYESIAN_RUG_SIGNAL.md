# Bayesian Rug Signal

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `SURVIVAL_MODEL.md`, `../../02-domain/DATA_MODEL/FEATURE_DICTIONARY.md`
Replaces: bayesian signal docs across source corpus

## Purpose

Define canonical Bayesian adjustment layer for rug timing probability.

## Scope

1. Prior from survival baseline.
2. Likelihood evidence from price/volatility/gap signals.
3. Posterior output for strategy and risk modules.

## Source Inputs

1. `PROBABILISTIC_REASONING.md`
2. `Statistical Opt/STATISTICAL-OPTIMIZATION/16-BAYESIAN-RUG-SIGNAL.md`
3. `bayesian prediction engine/files/README.md`

## Canonical Decisions

### 1) Model Structure

`posterior ∝ likelihood(features|rug) * prior(rug|tick)`

### 2) Evidence Families

1. price trajectory signals (`distance_from_peak`, momentum, volatility)
2. timing signals (`ticks_since_peak`, regime position)
3. stream integrity/gap signals (where available)

### 3) Output Contract

Minimum output:

- `p_rug_window_posterior`
- `confidence`
- `reason_codes` (top contributing factors)
- `model_version`

### 4) Safety Rule

No single heuristic multiplier should be treated as immutable constant; all adjustment strengths are model-versioned and evidence-backed.

## Open Questions

1. Should reason codes be standardized enum set in this section or in systems/event schema section?
