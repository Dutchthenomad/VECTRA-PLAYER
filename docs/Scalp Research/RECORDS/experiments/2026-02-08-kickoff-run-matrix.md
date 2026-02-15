# Scalping Kickoff Run Matrix

Date: 2026-02-08

This is the execution baseline for the first optimization cycle.

Status note:

- This kickoff matrix remains the baseline record.
- Active next-step policy testing now uses `SCALPING-V1-TOGGLE-TEST-MATRIX.md`.

## Planning Artifact

- Planner UI: `src/artifacts/tools/scalping-optimization-planner/index.html`
- Direct URL (local static server): `http://127.0.0.1:47911/tools/scalping-optimization-planner/index.html`

## Phase 1: Entry-First Search (Kickoff Baseline)

Mode:

- Bayesian search (`TPE/GP`)

Ranges:

- `classification_ticks`: `20..40`, step `5`
- `entry_cutoff_tick`: `30..60`, step `5`
- `hold_ticks`: `3,5,7,9`
- entry families: `momentum`, `pullback continuation`, `breakout`, `mean reversion`
- threshold profiles/family: `6`
- confidence gate levels: `3`

Trials and promotion:

- Stage A trials: `300` on `500` games
- Promotion rate: `15%`
- Stage B trials: `120` on `1772` games

## Phase 2: Exit Surface (Drift-Based)

Input candidate count:

- Stage 2 candidates: `30`

Ranges:

- Drift references: `P50`, `P75`, `P90`
- TP multipliers: `1..5`
- SL multipliers: `1..4`

## Phase 3: Monte Carlo Robustness

- MC candidates: `10`
- Paths/candidate: `10,000`
- Games/path: `500`
- Regime stress scenarios: `4`

## Soft Label Policy (Pre-Threshold)

- `Explore`: high utility + stable neighborhood
- `Avoid`: dominated profile or consistent downside failure
- `Noise`: unstable, low-support, or outlier-led

## Promotion Rule for Next Iteration

Promote only candidates that satisfy all:

1. Positive net SOL in Stage B.
2. No collapse under local parameter perturbation (`±1` hold, `±5` cutoff, `±1` TP/SL multiplier).
3. Positive median End SOL under baseline Monte Carlo regime mix.

## Deliverables Required from This Cycle

1. Entry-family ranking with supporting evidence.
2. Exit-surface plateaus (not only top single points).
3. Monte Carlo risk profile for top candidates.
4. Updated checkpoint JSON and dated markdown summary in this folder.
