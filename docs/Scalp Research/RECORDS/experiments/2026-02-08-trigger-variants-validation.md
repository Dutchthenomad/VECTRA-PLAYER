# Scalping Trigger Variants Validation (Larger Pass)

Last updated: 2026-02-08

## Purpose

Validate proposed trigger variants on a larger dataset and determine a tentatively validated higher-order method for entry/exit signal selection.

## Datasets

1. `min60` canonical set
- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
- `1,772` games

2. `min30` expanded set (larger pass)
- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min30.jsonl`
- `2,056` games

Note: attempted expansion from `/home/devops/rugs_recordings` added only a small number of deduped unique game-history IDs, so the `min30` export is the largest clean dataset for this pass.

## Simulation Protocol

To avoid multi-signal inflation:

1. Sequential simulation with one active trade at a time.
2. One trade maximum per game per variant.
3. Tick-level TP/SL/time exits.
4. No volume inputs.

## Variant Definitions (as tested)

### L1_EXPANSION_IMMEDIATE (Long)

- Entry on current tick `t` when:
- `r_t in [-25%, -15%]`
- prior-20-tick `peak >= 2.0x`
- prior-20-tick runup `>= 70%`
- retracement ratio in `[0.40, 0.55]`
- `abs10` (count of `|r| >= 10%` in last 10 ticks) in `[2, 4]`
- Exit: `TP 5%`, `SL 5%`, `max_hold 5`

### L2_EXPANSION_CONFIRMED (Long)

- Same core context as L1 (slightly wider retracement window `[0.35, 0.60]`, `abs10` in `[1,4]`)
- Plus confirmation: next tick `r_{t+1} > 0.5%`
- Entry at `t+1`
- Exit: `TP 3%`, `SL 4%`, `max_hold 3`

### L3_HYBRID_SPLIT (Long)

- L1 context gate
- 50% notional immediate leg: `TP 4%`, `SL 5%`, `hold 5`
- 50% notional confirmed leg (if `r_{t+1} > 0`): `TP 3%`, `SL 4%`, `hold 3`
- Reported return is weighted composite of executed legs

### HOS_V1_SCORE_ROUTED (Higher-Order Long)

Candidate only when current tick is downside impulse (`r_t in [-25%, -15%]`).

Score components (`0..6`):

1. `peak >= 2.0x`
2. runup in `[70%, 150%]`
3. retracement in `[0.40, 0.55]`
4. `abs10 in {2,3}`
5. `entry/sma20 in [0.85, 1.08]`
6. `r_{t+1} > 0`

Routing:

- Route A (confirmed): if `score >= 5` and `r_{t+1} > 0.5%`, enter `t+1`, `TP 3.5%`, `SL 4%`, `hold 4`
- Route B (fallback): else if `score >= 4`, enter `t`, `TP 5%`, `SL 5%`, `hold 5`

### S1_BLOWOFF_STRICT_SHORT (Experimental)

- Previous tick blowoff:
- `r_{t-1} in [+15%, +25%]`
- previous tick is local peak
- prior runup `>= 100%`
- previous price `>= 2.0x`
- current tick red `<= -1%`
- `abs10 == 2`
- `entry/sma20 >= 1.0`
- Entry at `t` short
- Exit: `TP 1%`, `SL 3%`, `hold 5`

## Results (One Trade Per Game)

### `min60` (`1,772` games)

- `L1_EXPANSION_IMMEDIATE`: `n=319`, win `65.8%`, mean/med `+2.96% / +2.74%`
- `L2_EXPANSION_CONFIRMED`: `n=279`, win `60.9%`, mean/med `-0.01% / +1.10%`
- `L3_HYBRID_SPLIT`: `n=468`, win `65.6%`, mean/med `+1.63% / +2.25%`
- `HOS_V1_SCORE_ROUTED`: `n=1,054`, win `68.8%`, mean/med `+2.66% / +3.16%`
- `S1_BLOWOFF_STRICT_SHORT`: `n=101`, win `52.5%`, mean/med `+2.51% / +1.03%`

### `min30` (`2,056` games, larger pass)

- `L1_EXPANSION_IMMEDIATE`: `n=324`, win `66.4%`, mean/med `+3.06% / +2.76%`
- `L2_EXPANSION_CONFIRMED`: `n=284`, win `61.3%`, mean/med `+0.07% / +1.17%`
- `L3_HYBRID_SPLIT`: `n=479`, win `66.0%`, mean/med `+1.66% / +2.27%`
- `HOS_V1_SCORE_ROUTED`: `n=1,080`, win `68.9%`, mean/med `+2.63% / +3.19%`
- `S1_BLOWOFF_STRICT_SHORT`: `n=101`, win `52.5%`, mean/med `+2.51% / +1.03%`

## Stability Notes

### HOS_V1 (min30 split checks)

- By-day results were mostly consistent positive, with one small-sample weak day (`20260105`, `n=21`).
- Hash split stability:
- odd: `n=549`, mean `+2.28%`, median `+3.00%`
- even: `n=531`, mean `+2.99%`, median `+3.41%`

Interpretation: higher-order long method is reasonably stable for a tentative V1.5 research policy.

### S1 Short (min30 split checks)

- Hash split instability:
- odd: stronger positive
- even: notably weaker / negative median

Interpretation: short setup remains experimental; do not promote to primary policy.

## Tentatively Validated Method (Current)

Primary candidate: `HOS_V1_SCORE_ROUTED` (long only), with:

1. Feature-score gate (6-component state quality test).
2. Route-to-entry logic (confirmed route preferred, immediate fallback).
3. Fixed TP/SL/time exits tied to route.

Why this method:

- Higher coverage than narrow L1 while preserving strong median returns.
- More stable than short-side candidates.
- Consistent behavior across `min60` and larger `min30` set.

## Practical Deployment Guidance (Research Mode)

1. Promote `HOS_V1_SCORE_ROUTED` as the default exploratory policy.
2. Keep `L1` and `L3` as comparison baselines.
3. Keep `S1` short in low-weight sandbox mode only.
4. Add confidence/risk gating:
- no-trade zone when score is marginal and post-impulse reaction is ambiguous.

## Remaining Gaps Before Production Claims

1. Include fee/rake adjustments in PnL accounting.
2. Run strict walk-forward date validation (train windows vs holdout windows).
3. Stress-test sensitivity to threshold drift (`runup`, `retr`, `abs10`, SMA band).
4. Add bootstrap confidence intervals around mean/median outcomes.
