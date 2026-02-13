# 05 Evaluation Protocol

Status: active
Last validated: 2026-02-08

## Objective

Define a leakage-resistant evaluation workflow for strategy search, validation, and promotion.

## Stage Model

1. Stage A: quick search on reduced dataset (`quick500`) for candidate triage.
2. Stage B: confirmation on canonical full dataset (`min60`).
3. Stage C: robustness testing with sequence resampling / regime-mix stress.

## Required Split Hygiene

Never pick and evaluate on the same sample without explicit "in-sample only" labeling.

Minimum acceptable protocol:

1. Train split: select thresholds/permutation.
2. Validation split: compare/select candidate families.
3. Test split: final report only.

Preferred extension:

1. Walk-forward windows for temporal leakage reduction.

## Optimization Order

1. Entry modeling (signal quality).
2. Exit surface calibration (TP/SL/time).
3. Robustness checks and promotion governance.

## Baseline Search Space (Current Practical Band)

1. `classification_ticks`: `20..25` (extended studies can scan wider).
2. `entry_cutoff_tick`: `50..60`.
3. `max_hold_ticks`: `7..9`.
4. Playbook focus: `P1_MOMENTUM` and `AUTO_REGIME` baselines.
5. Drift references: `P90` primary, `P75/P50` robustness.
6. TP/SL multipliers: focus around `2..4` for both, then widen if needed.

## Core Metrics

1. Coverage:
- trade count,
- participation rate,
- no-trade collapse frequency.

2. Return:
- mean/median return or net SOL,
- end SOL distribution.

3. Downside:
- p10/p05 outcomes,
- worst-game outcomes,
- max drawdown (if sequential bankroll simulation enabled).

4. Stability:
- date split consistency,
- hash partition consistency,
- local parameter perturbation resilience.

## Soft Labels Before Hard Promotion

1. `Explore`: strong utility and stable neighborhood.
2. `Avoid`: dominated or downside-failing profile.
3. `Noise`: unstable or outlier-dependent.

## Promotion Gate

Candidate is promotable only if all pass:

1. Positive central tendency in out-of-sample checks.
2. Acceptable downside anchors (not only top-end outliers).
3. No severe collapse under local perturbation.
4. Stable behavior across independent splits.

## Mandatory Reporting Artifacts

1. Dated experiment record in `../RECORDS/experiments/`.
2. Checkpoint JSON references in `../RECORDS/checkpoints/`.
3. Canonical results update in `06_RESULTS_CANONICAL.md` only when evidence bar is met.

## Related Records

1. `../RECORDS/experiments/2026-02-08-kickoff-run-matrix.md`
2. `../RECORDS/experiments/2026-02-08-kickoff-run-results.md`
3. `../RECORDS/experiments/2026-02-08-v1-toggle-test-matrix.md`
