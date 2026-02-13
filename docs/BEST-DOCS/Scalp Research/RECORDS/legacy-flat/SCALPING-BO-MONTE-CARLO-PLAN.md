# Bayesian Optimization + Monte Carlo Execution Plan

Date: 2026-02-08

This is the concrete run plan for moving from exploratory insight to robust strategy candidates.

## Phase 0: Baseline Integrity

1. Use canonical dataset exports.
2. Verify artifact controls and run path.
3. Confirm checkpoint metrics are reproducible.

## Phase 1: Entry-First Bayesian Search

Goal:

- Identify signal families/thresholds with durable edge before heavy exit tuning.

Protocol:

1. Freeze exits initially (time-exit baseline).
2. Search entry parameters with Bayesian optimization (TPE or GP+EI).
3. Multi-fidelity:
- Stage A quick set: `min60_quick500`
- Stage B full set: `min60`

Candidate search dimensions:

- `classification_ticks`: 20..40
- `entry_cutoff_tick`: 30..60
- `max_hold_ticks`: 3..9
- entry family thresholds (momentum/pullback/breakout/reversion)
- optional regime confidence gates

Primary scoring shape:

- maximize central tendency and downside-aware utility
- avoid pure-mean optimization

## Phase 2: Exit Surface Optimization (Drift-Based)

Goal:

- Optimize exits only after strong entries are selected.

Protocol:

1. Keep top entry candidates fixed.
2. Sweep drift anchors (`P50`, `P75`, `P90`) and TPx/SLx ranges.
3. Evaluate permutation surfaces in SOL terms.

Key output:

- Plateau regions (robust zones), not isolated peaks.

## Phase 3: Soft Labeling Before Hard Thresholds

Goal:

- Triage parameter zones before rigid gates.

Labels:

- `Explore`: upper utility and stable neighborhood.
- `Avoid`: dominated or downside failures.
- `Noise`: unstable, low support, or outlier-led.

## Phase 4: V1 Toggle Policy Stress (Pre-Monte Carlo)

Goal:

- Validate whether profile toggles improve downside control without killing participation.

Protocol:

1. Use V1 simulator presets and controlled toggle matrix.
2. Evaluate regime participation toggles (`ALL` vs `trend_up+expansion`).
3. Evaluate SL strictness and risk-mode toggles.
4. Promote only candidates that improve downside anchors while preserving usable trade flow.

Reference matrix:

- `SCALPING-V1-TOGGLE-TEST-MATRIX.md`

## Phase 5: Monte Carlo Robustness (Recorded Games)

Goal:

- Stress-test candidate strategies under sequence variability and regime-mix uncertainty.

Protocol:

1. Bootstrap games with replacement (thousands of paths).
2. Run strategy on each simulated sequence.
3. Track terminal/end SOL distribution and drawdown characteristics.

Required outputs:

- End SOL: p5/p50/p95
- Probability of bankroll loss
- Max drawdown distribution
- Probability of ruin (if bankroll floor is defined)
- Sensitivity to regime reweighting

## Phase 6: Promote to Candidate Set

Promotion criteria:

1. Positive median End SOL under base distribution.
2. Acceptable downside profile under stress.
3. Local parameter stability (small perturbations do not collapse performance).

## Immediate Next Run Checklist

1. Use V1 toggle matrix on quick500 to shortlist policies.
2. Confirm shortlist on full `min60` dataset.
3. Apply soft labels (`Explore`, `Avoid`, `Noise`) to policy neighborhoods.
4. Monte Carlo stress-test top `Explore` policies.
5. Promote only if downside anchors and stability pass thresholds.
