# Scalping TA Toolkit Brainstorm (Price-Only + Bayesian)

Last updated: 2026-02-08

## Purpose

This document captures the TA and regime-identification ideas brainstormed for the rugs scalping research program.

Key context:

- We are grounding this system in source mechanics documented in `docs/rosetta-stone/ROSETTA-STONE.md`.
- This is a gamified, PRNG-driven candlestick simulation.
- Volume-based market tools do not apply (no real order book/market microstructure volume signal).
- Price and tick-time can still be converted into strong state estimators.

## Source-Mechanics Anchors (Why This Approach)

From the source mechanics in `ROSETTA-STONE.md`:

1. Rug is checked before drift each tick with fixed per-tick hazard `RUG_PROB = 0.005`.
2. Price moves come from branch logic:
- big move branch (`BIG_MOVE_CHANCE = 0.125`, size band `15%..25%`, random direction)
- drift+noise branch (`DRIFT_MIN=-2%`, `DRIFT_MAX=+3%`, volatility tied to `sqrt(price)`)
3. God candle branch exists but is extremely rare and capped by a `price <= 100x` condition.
4. Each game path is deterministic once `serverSeed + '-' + gameId` is known, but hidden during live play.

Implication: we should estimate latent branch/state probabilities in real time, not rely on static chart heuristics alone.

## Design Principle

Use TA features as **state estimators** and combine them with a **mechanistic Bayesian layer**.

- TA provides interpretable local structure (trend pressure, overextension, compression/expansion).
- Bayesian layer fuses those signals into posterior regime probabilities and trade-quality estimates.

## A) Mechanistic/Bayesian Regime Toolkit

### A1. Branch-Likelihood Signals

Per tick, estimate:

- `P_jump` (current behavior matches big-move branch)
- `P_drift_up`
- `P_drift_down`
- `P_chop`
- `P_uncertain`

These are posterior probabilities, not hard labels.

### A2. Rug Survival and Hold-Risk Math

Given fixed per-tick rug hazard `h = 0.005`:

- survival over `H` ticks: `S(H) = (1 - h)^H`
- rug risk over `H` ticks: `R(H) = 1 - (1 - h)^H`

Examples:

- `H=5` -> `R(5) ≈ 2.48%`
- `H=10` -> `R(10) ≈ 4.89%`
- `H=20` -> `R(20) ≈ 9.54%`

This should directly constrain max hold policy.

### A3. Peak/Continuation Probability Metrics

Use posterior quantities:

- `P(new_high_before_rug | state)`
- `P(peak_already_reached) = 1 - P(new_high_before_rug | state)`

This is preferable to attempting direct peak prediction.

### A4. Actionable Regime Set (Candidate)

- `Drift Up`
- `Drift Down`
- `Jump Expansion`
- `Chop Mean-Revert`
- `No Edge / Uncertain`

## B) Converted Price-Only TA Tools

These are valid because they require only price/tick data.

### B1. Trend Pressure

- SMA/EMA slopes and fast/slow cross states
- EMA spread normalized by ATR-like scale

### B2. Momentum/Overextension

- RSI (short windows suited for tick data)
- MACD histogram slope (acceleration/deceleration)

### B3. Volatility/Compression

- Bollinger Bands:
- `%B` for location in band
- band width for compression vs expansion
- ATR-style tick volatility estimate (normalized)

### B4. Structure/Breakout

- Donchian channel breakout distance
- distance from rolling high/low
- breakout confirmation checks

### B5. Optional Context Tools

- Fibonacci retracement as a contextual structure overlay only (not a primary trigger)

## C) Non-Volume Feature Family (Custom to This Game)

### C1. Duration-State Features

- `tick_age` (current tick index)
- `age_percentile` vs historical duration CDF
- hold viability by horizon (`H` ticks)

### C2. Path Features

- `running_peak`, `running_trough`
- distance to peak/trough
- `new_high_rate` in recent window
- drawdown depth from local peak

### C3. Generator-Aware Features

- jump-event proxy frequency (rolling)
- jump polarity skew
- drift mean and drift sigma after filtering jump-like returns
- expansion pressure (late-vs-early realized absolute return ratio)

## D) GameHistory Prior Layer (Cross-Game Context)

Use recent game peaks as Bayesian priors, not deterministic forecasts.

Example thresholds:

- `P(peak >= 2x)`
- `P(peak >= 10x)`
- `P(peak >= 50x)`
- `P(peak >= 100x)`

Important modeling rule:

- Treat thresholds as nested tails (`100x ⊂ 50x ⊂ 10x ⊂ 2x`).
- Prefer conditional/hierarchical estimation over independent binomial estimates.
- Use shrinkage to long-run priors because high-tier events are sparse.

Suggested context windows:

- last 100 games for stable tail priors
- last 10 full games for recency path characteristics

## E) Composite Decision Panel (Research Candidate)

Three-panel live decision framework:

1. `Tail Opportunity`
- posterior chance of high-upside continuation / new highs

2. `Path Quality`
- trend coherence vs jump/chop contamination

3. `Rug-Over-Hold Risk`
- horizon-dependent ruin risk based on planned hold ticks

Derived scalar (optional):

- `Scalp Opportunity Index` (0-100), combining the three with explicit weights.

## F) Candidate Alpha Hypotheses for High-Tier Players

1. Drift continuation edge is strongest when trend pressure and path quality agree.
2. Pullback continuation edge improves when jump contamination is low.
3. Mean-reversion edge improves after downside jump signatures with reflex confirmation.
4. Breakout edge is strongest when compression resolves into expansion with positive momentum.
5. Expected value collapses quickly when rug-over-hold risk rises while edge confidence falls.

## G) Guardrails and Anti-Patterns

- Do not use volume-derived indicators (VWAP, OBV, MFI, order-flow tools).
- Do not treat deterministic post-game verification as live predictability.
- Do not use single threshold triggers without posterior confidence/risk context.
- Do not overfit rare high-tier events (50x/100x) without shrinkage and stress tests.

## H) Practical Next-Step Questions

1. Which 5-7 features are most orthogonal for a minimal V2 regime model?
2. What posterior confidence is required before entry?
3. Which horizons (`H`) are primary for scalping (3, 5, 8 ticks)?
4. How should trade gating change as `R(H)` rises with longer holds?

## I) Trigger Variants (Current Draft Set)

### I1. L1 Expansion Immediate (Long)

- Enter on downside impulse inside expansion pullback context.
- Typical envelope:
- impulse: `-15%..-25%`
- local runup present (`>=70%`)
- retrace near mid-band (`~40%-55%`)

### I2. L2 Expansion Confirmed (Long)

- Same expansion pullback context, but require early rebound confirmation (`r1 > 0`) before entry.
- Designed to avoid immediate cascade failures.

### I3. L3 Hybrid Split (Long)

- Partial immediate entry + partial confirmation entry.
- Balances early capture with confirmation safety.

### I4. S1 Blowoff Strict (Short, Experimental)

- Designed for post-blowoff fade only under strict context.
- Remains experimental due stability concerns in split checks.

### I5. HOS_V1 Score-Routed (Higher-Order Long)

- Multi-feature score gate with route selection:
- confirmed route when score is high and reaction confirms
- fallback immediate route when score is high but confirmation is weaker

Reference validation: `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md`

## J) Current Priority Order (Tentative)

1. `HOS_V1 Score-Routed` (primary exploratory policy)
2. `L1` and `L3` (baseline comparators)
3. `L2` (confirmation-heavy benchmark)
4. `S1` short (sandbox only)

## K) Review Rule

- Any future trigger change should be accepted only if it improves:
- median return,
- downside tail control,
- and split stability across independent partitions.
