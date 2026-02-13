# Feature Dictionary

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `CANONICAL_DATASETS.md`, `../../03-strategy-and-math/README.md`
Replaces: feature definitions spread across ML and analysis docs

## Purpose

Define core feature names and meanings used across probability, risk, and RL models.

## Scope

Baseline feature vocabulary for v1 strategy-and-math integration.

## Source Inputs

1. `Machine Learning/models/sidebet-v1/design/OBSERVATION_SPACE_v1.md`
2. `PROBABILISTIC_REASONING.md`
3. `risk_management/README.md`
4. `Statistical Opt/RL-TRAINING/19-SIDEBET-RL-ENVIRONMENT.md`

## Canonical Feature Baseline (v1)

| Feature | Type | Unit | Description |
|---|---|---|---|
| `tick` | int | tick | Current round tick index. |
| `price` | float | multiplier | Current observed multiplier/price. |
| `running_peak` | float | multiplier | Highest observed price so far in round. |
| `ticks_since_peak` | int | tick | Tick distance from running peak. |
| `volatility_10` | float | normalized | Rolling 10-tick volatility measure. |
| `momentum_5` | float | normalized | Rolling 5-tick momentum estimate. |
| `distance_from_peak` | float | ratio | Relative distance below running peak. |
| `p_rug_window` | float | probability | Estimated probability of rug within sidebet window. |
| `can_place_sidebet` | bool | - | Eligibility flag based on domain constraints. |
| `is_unplayable` | bool | - | True when round constraints invalidate strategy entry window. |

## Canonical Decisions

1. Feature names are snake_case.
2. Every feature must define derivation window and normalization assumptions in Section 4 docs.
3. Feature changes require changelog entry in strategy section and impacted schema notes.

## Open Questions

1. Should feature dictionary include mandatory null-handling semantics at domain level?
