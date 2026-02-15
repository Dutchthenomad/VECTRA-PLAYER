# Strategy and Math

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `../00-governance/CONSTANTS_AND_SEMANTICS.md`, `../02-domain/README.md`
Replaces: strategy/math guidance scattered across source corpus

## Purpose

Define canonical quantitative models and strategy interfaces for probability, risk, optimization, and RL.

## Scope

1. Rug timing probability models.
2. Risk and sizing logic.
3. Optimization and simulation methodology.
4. RL environment and observation/action/reward contracts.

## Contents

1. `PROBABILITY/README.md`
2. `PROBABILITY/SURVIVAL_MODEL.md`
3. `PROBABILITY/BAYESIAN_RUG_SIGNAL.md`
4. `RISK/README.md`
5. `RISK/POSITION_SIZING.md`
6. `RISK/DRAWDOWN_CONTROL.md`
7. `RISK/RISK_METRICS.md`
8. `OPTIMIZATION/README.md`
9. `OPTIMIZATION/MONTE_CARLO.md`
10. `OPTIMIZATION/STRATEGY_PROFILE_GENERATION.md`
11. `RL/README.md`
12. `RL/RL_ENVIRONMENT_SPEC.md`
13. `RL/OBSERVATION_ACTION_REWARD.md`

## Primary Source Inputs

1. `PROBABILISTIC_REASONING.md`
2. `risk_management/README.md`
3. `risk_management/IMPLEMENTATION_GUIDE.md`
4. `Statistical Opt/STATISTICAL-OPTIMIZATION/*.md`
5. `Statistical Opt/RL-TRAINING/19-SIDEBET-RL-ENVIRONMENT.md`
6. `Machine Learning/models/sidebet-v1/design/*.md`

## Canonical Decisions

1. Mathematical semantics follow governance constants and payout notation.
2. Models must separate descriptive statistics from decision policy thresholds.
3. Strategy docs must specify required inputs, outputs, and failure modes.

## Open Questions

1. Should Section 4 publish one unified “decision pipeline” diagram linking all submodels?
