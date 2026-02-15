# 04 Strategy and Feature Catalog

Status: active
Last validated: 2026-02-08

## Purpose

Define the strategy families and feature groups currently used or explored for scalping research.

## Baseline Playbook Families

1. `P1_MOMENTUM`: short-horizon continuation.
2. `P2_PULLBACK_CONT`: continuation after shallow pullback in up pressure.
3. `P3_MEAN_REVERT`: snapback after short-horizon overreaction.
4. `P4_BREAKOUT`: local-high break with confirming momentum.

## Higher-Order Trigger Variants (Research)

1. `L1_EXPANSION_IMMEDIATE` (long)
- Immediate entry on constrained downside impulse in expansion context.

2. `L2_EXPANSION_CONFIRMED` (long)
- Same context as L1 with one-tick rebound confirmation before entry.

3. `L3_HYBRID_SPLIT` (long)
- Combined immediate + confirmed legs.

4. `HOS_V1_SCORE_ROUTED` (higher-order long, current primary exploratory policy)
- Multi-feature score gate with route selection:
  - confirmed route when state quality and reaction confirm,
  - immediate fallback route when score remains acceptable.

5. `S1_BLOWOFF_STRICT_SHORT` (short, experimental)
- Narrow post-blowoff short setup.
- Kept sandbox-only pending stronger stability evidence.

## Feature Families (Price/Tick Only)

## A) Mechanistic/Bayesian State Features

1. Branch-likelihood proxies (`jump`, `drift_up`, `drift_down`, `chop` tendencies).
2. Rug-over-horizon risk for hold horizon `H`:
- `R(H) = 1 - (1 - h)^H`, `h = 0.005` (mechanics-based baseline).
3. Peak-continuation descriptors:
- probability-oriented framing (`new_high_before_rug`, `peak_likely_reached` style metrics).

## B) Converted TA Features (No Volume Inputs)

1. Trend pressure: SMA/EMA slope and spread behavior.
2. Momentum: RSI/MACD-style short-window acceleration.
3. Volatility/compression: Bollinger width, ATR-like tick volatility.
4. Structure: Donchian breakout distance and local range location.

## C) Custom Path Features

1. `tick_age` and age percentile vs duration history.
2. Running peak/trough distance and drawdown depth.
3. Recent large-move count and polarity skew.
4. Expansion pressure and sign-flip behavior.

## D) Cross-Game Prior Layer

Use rolling game-history threshold priors as context, not deterministic forecasts:

1. `P(peak >= 2x)`
2. `P(peak >= 10x)`
3. `P(peak >= 50x)`
4. `P(peak >= 100x)`

Nested-tail/hierarchical treatment is preferred over independent-binomial treatment.

## Guardrails

1. No volume/order-book indicators.
2. No deterministic claims from post-reveal PRNG properties during live-state inference.
3. No promotion based on mean-only improvements without downside and split checks.

## Evidence Reference

1. Trigger validation record:
- `../RECORDS/experiments/2026-02-08-trigger-variants-validation.md`
2. Long/short edge study:
- `../RECORDS/experiments/2026-02-08-long-short-edge-study.md`
3. Original TA brainstorm:
- `../RECORDS/legacy-flat/SCALPING-TA-TOOLKIT-BRAINSTORM.md`
