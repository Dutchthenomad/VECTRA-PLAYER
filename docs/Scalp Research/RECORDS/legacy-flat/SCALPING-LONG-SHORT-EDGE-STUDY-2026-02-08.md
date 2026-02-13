# Scalping Long/Short Edge Study (Real Games)

Last updated: 2026-02-08

## Scope

This checkpoint extends the real-game tick study to:

1. Validate expansion pullback long behavior from actual recordings.
2. Test short-side entry windows for robust scalp viability.
3. Produce a practical conclusion for what to prioritize in V2.

Dataset used:

- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
- `1,772` games (minimum 60 ticks each)

## Mechanics Note (Short Side)

Short PnL in current docs is marked tentative:

- `pnl = amount * (entryPrice - currentPrice) / entryPrice`
- Source: `docs/rosetta-stone/ROSETTA-STONE.md` (`shortPosition` section)

This study uses the corresponding short return proxy:

- `short_return = entry / exit - 1`

No fee/rake correction is applied in this checkpoint.

## A) Long-Side Findings (Expansion Pullback Rebound)

### A1. Broad Pattern

Pattern definition (deduped by game + entry tick):

- strong run-up context in prior window
- pullback from local high
- entry on large down-impulse tick
- evaluate next 5 ticks

Results:

- `n=555` events across `423` games
- `hit +5% within 5 ticks`: `39.8%`
- `drop <= -5% within 5 ticks`: `26.5%`
- `r5 mean/median`: `+1.84% / +1.78%`

Baseline comparison (`all big-down ticks -15%..-25%`):

- `n=13,031`
- `hit +5%`: `40.6%`
- `drop <= -5%`: `27.2%`
- `r5 mean/median`: `+1.68% / +2.03%`

Interpretation: broad pattern exists, but naive definition is only slightly better than baseline.

### A2. Concentrated Long Edge Zone

Best observed concentration in this pass:

- pullback depth near `40%..50%` of prior run-up amplitude
- recent large-move count in last 10 ticks around `2` (active, not chaotic)

Subset result:

- `n=42`
- `hit +5% within 5 ticks`: `54.8%`
- `drop <= -5% within 5 ticks`: `16.7%`
- `r5 mean/median`: `+7.38% / +3.23%`

Quick-response profile in same subset:

- `+2% within 2 ticks`: `50.0%`
- `+3% within 3 ticks`: `47.6%`

Interpretation: this is the strongest observed real-game scalp pocket in this checkpoint.

## B) Short-Side Findings

### B1. Naive Shorting of Big-Up or Breakdown Ticks

Shorting generic high-volatility ticks was not robust on median outcomes.

Examples:

- `ALL big-up ticks (+15%..+25%)`: `n=13,107`, 5-tick median about `-2.09%`, adverse tails frequent.
- `ALL big-down ticks (-15%..-25%)`: similarly weak for short continuation on median.

Means were occasionally positive due tail outliers (near-rug collapses), but medians remained negative.

### B2. Blow-Off + First Red Diagnostic (Important)

Diagnostic split (not directly tradable at the same timestamp):

- if next tick after blow-off is red: short outcomes improve materially
- if next tick is green: short outcomes deteriorate materially

This is useful as a classifier signal, not a standalone entry rule.

### B3. Tradable Strict Confirmed Short Niche (Small Sample)

Strict entry (tradable timing, no lookahead leakage):

- previous tick is big-up (`+15%..+25%`)
- previous tick is local peak
- prior run-up >= `100%` with prior peak >= `2.0x`
- current tick is red (`<= -1%`)
- entry still above SMA20 (`>=1.0x` ratio)
- recent absolute large-move count (`abs10`) equals `2`

Sample:

- `n=97` entries across `91` games

Raw 5-tick outcome:

- median `-0.70%`, mean `+3.13%` (skewed by right-tail winners)

Best risk-managed settings in this sample:

- `TP=1%`, `SL=3%`, hold `5` ticks:
- median `+1.03%`, trimmed mean `+2.19%`, adverse <=`-5%` about `15.5%`

### B4. Stability Check

Split behavior was unstable:

- hash-odd split positive
- hash-even split negative

Interpretation: short niche is promising as a hypothesis, but not yet reliable enough to treat as a primary edge.

## C) Logical Conclusion (Current)

1. The strongest current edge remains **long-side expansion pullback rebound** with tight contextual filters.
2. Short-side scalp entries are **not yet robust** as a general strategy.
3. Short should stay in **experimental/secondary mode** until stability improves across splits and larger samples.

## D) Practical Guidance for V2 Design

### D1. Promote to Primary Research Track

- Long rebound playbook around expansion pullback with concentrated filters.
- Add reaction-state classifier to separate rebound vs cascade after impulse.

### D2. Keep as Secondary Track

- Strict-confirmed short niche (`n=97`) with small TP and tight controls.
- Use low weighting/size in simulations until cross-validated.

### D3. Additional Edge Ideas to Document and Test

1. First-post-impulse reaction classifier:
- `r1 > 0` vs `r1 <= 0` as a high-value branch signal.

2. Dynamic hold by hazard:
- constrain hold by rug-over-horizon risk and regime confidence.

3. GameHistory prior context:
- use rolling peak-threshold priors (`2x/10x/50x/100x`) as Bayesian context, not deterministic prediction.

4. Skip/no-trade zones:
- explicitly model and avoid states with strong bounce-cascade ambiguity.

## E) What This Means for “Short at Optimal Place”

Current answer from real-game evidence:

- There is no broad, always-on short scalp edge from simple blow-off or breakdown signals.
- A narrow short setup may exist, but it is not yet stable enough to be considered production-grade.
- Priority should remain long-edge optimization plus better cascade/rebound classification before scaling short usage.

## F) Follow-On Validation

See `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md` for the larger-pass trigger benchmark (`min60` + `min30`) and the current tentative higher-order candidate (`HOS_V1 Score-Routed`).
