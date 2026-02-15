# 03 System Model: Classification and Regimes

Status: active
Last validated: 2026-02-08

## System Layers

For each game, decision flow is:

1. Classifier (one-time early-window regime label).
2. Regime router (allowed playbooks).
3. Playbook signal checks (entry triggers).
4. Exit engine (TP/SL/time).

## Classifier Input Window

1. Uses first `classificationTicks + 1` prices.
2. Effective window is lower-bounded by implementation safety logic (minimum baseline size).
3. If data is insufficient, classifier returns `uncertain`.

## Core Features

1. `momentumWindow`: return from window start to end.
2. `momentumTail`: recent local momentum in final subwindow.
3. `vol`: return standard deviation.
4. `range`: in-window max/min envelope.
5. `signFlips`: count of direction changes.
6. `expansionRatio`: late absolute return intensity vs early intensity.

## Regime Labels

1. `trend_up`
2. `trend_down`
3. `expansion`
4. `chop`
5. `uncertain`

## Decision Order

Order is deterministic and first-match wins:

1. `trend_up`
2. `trend_down`
3. `expansion`
4. `chop`
5. `uncertain`

If multiple conditions would match, earlier checks dominate later checks.

## AUTO Regime Routing Map

1. `trend_up` -> `P1_MOMENTUM`, `P2_PULLBACK_CONT`
2. `trend_down` -> `P3_MEAN_REVERT`
3. `expansion` -> `P4_BREAKOUT`, `P1_MOMENTUM`
4. `chop` -> `P3_MEAN_REVERT`
5. `uncertain` -> no trade

## Fixed Playbook vs AUTO

1. `AUTO_REGIME`: applies regime gate map.
2. Fixed playbook mode: bypasses regime gating and evaluates only selected playbook.

## Practical Implications

1. Increasing `classificationTicks` changes both evidence window and threshold scaling behavior.
2. `AUTO_REGIME` can intentionally produce no-trade outputs in `uncertain` conditions.
3. Regime explanation and entry explanation are separate:
- regime says which family is allowed,
- playbook says why a specific tick was entered.

## Code Truth References

1. `src/artifacts/tools/scalping-bot-v1-simulator/main.js`
2. `src/artifacts/tools/scalping-explorer/main.js`
3. Original plain-language primer record:
- `../RECORDS/legacy-flat/SCALPING-CLASSIFICATION-AND-REGIME-PRIMER.md`
