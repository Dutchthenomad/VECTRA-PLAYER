# 01 Scope and Assumptions

Status: active
Last validated: 2026-02-08

## Objective

Define the exact research scope for offline scalping optimization and prevent scope drift.

## In Scope

1. Offline replay on prerecorded full-game tick series (`prices[]`).
2. Early-window classification and regime-aware routing.
3. Long-first trigger development with short-side sandbox research.
4. Exit modeling with TP/SL/time constraints.
5. SOL-based outcome reporting at trade and game aggregation levels.

## Out of Scope (Current)

1. Live trading integration.
2. Latency modeling.
3. Slippage modeling.
4. Full execution-truth reconciliation with live account events.
5. Production deployment claims.

## Core Mechanics Assumptions

1. One active position at a time.
2. Entry scan starts at `classificationTicks + 1`.
3. No new entries after configured cutoff tick.
4. TP/SL/time exits are deterministic within replayed tick paths.
5. Strategy quality is judged by both return and downside anchors.

## Strategy Scope Clarification

1. Primary research path is long-side optimization.
2. Short-side work is permitted in sandbox mode only.
3. Short-side policies cannot be promoted to primary without split-stability evidence.

## Canonical Definitions

1. `Classification Ticks`: number of early ticks used for one-time regime inference.
2. `No-New-Entry After Tick`: hard gate for opening trades.
3. `Max Hold Ticks`: forced exit horizon.
4. `One-Tick Drift Reference`: percentile anchor (`P50/P75/P90`) used to scale TP/SL.
5. `TPx/SLx`: integer multipliers applied to selected drift reference.
6. `Net SOL`: cumulative trade PnL in SOL.
7. `End SOL`: starting bankroll + net SOL.

## Modeling Priority Rule

1. Entry quality first.
2. Exit calibration second.
3. Robustness and promotion governance third.

## Policy for Canonical Truth

1. Facts require reproducible evidence from checkpoints/records.
2. Hypotheses must be clearly labeled as exploratory.
3. Canonical metrics should be referenced from `06_RESULTS_CANONICAL.md`.
