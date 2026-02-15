# 08 Roadmap and Decision Rules

Status: active
Last validated: 2026-02-08

## Objective

Define near-term execution order and promotion/rejection criteria for strategy development.

## Current Priority Stack

1. Preserve and validate long-side score-routed edge (`HOS_V1` family).
2. Improve downside governance (split stability, perturbation resilience, path-risk metrics).
3. Keep short-side as exploratory sandbox until stability standards are met.

## Roadmap Phases

## Phase 1: Evaluation Hygiene Hardening

1. Enforce split-aware selection/reporting.
2. Add walk-forward validation mode.
3. Standardize downside anchors and uncertainty outputs.

## Phase 2: Exit and Regime Calibration

1. Refit TP/SL surfaces conditioned on horizon and regime behavior.
2. Measure TP/SL activation rates vs time-exit dominance.
3. Tighten no-trade and ambiguity gates.

## Phase 3: Robustness Promotion

1. Monte Carlo sequence resampling.
2. Regime-mix stress checks.
3. Promotion only when central tendency and downside constraints both pass.

## Phase 4: V2 Integration Readiness

1. Maintain offline-online parity targets.
2. Keep pipeline contract issues tracked and resolved before live subscription.
3. Reconcile feature schema and scoring assumptions with pipeline outputs.

## Decision Rules

## Canonical Fact Rule

A claim may be treated as canonical only if:

1. It is reproducible from checkpoint/record artifacts.
2. It is represented in `06_RESULTS_CANONICAL.md`.
3. It is not contradicted by newer higher-quality evidence.

## Strategy Promotion Rule

A strategy is promotable only if:

1. Out-of-sample central tendency is positive.
2. Downside anchors remain within accepted bounds.
3. Split stability and local perturbation checks pass.
4. Participation is non-trivial (not no-trade collapse).

## Rejection Rule

Reject or sandbox any candidate with:

1. Outlier-driven mean without median/downside support.
2. Split instability.
3. Extreme sensitivity to small threshold changes.

## Active Hypothesis Backlog (Condensed)

1. Entry quality dominates exit tuning in long-run utility.
2. Regime-conditioned routing outperforms one-policy universality.
3. First-25-tick signatures can improve state quality separation.
4. Drift-scaled exits can transfer better than fixed-percentage exits.
5. Explicit no-trade zones may improve downside-adjusted returns.

Detailed backlog reference:

- `../RECORDS/legacy-flat/SCALPING-THEORETICAL-AVENUES.md`

## Session Resume Anchor

When resuming work, use:

1. `06_RESULTS_CANONICAL.md`
2. `07_RISK_AND_LIMITATIONS.md`
3. latest experiment records in `../RECORDS/experiments/`
