# Scalping V1 Toggle Test Matrix

Date: 2026-02-08

This matrix defines the immediate controlled experiments for the V1 bot simulator.

## Objective

Convert the current V1 signal into a robust policy by testing toggle combinations that directly target downside containment and regime noise.

## Fixed Baseline

Hold constant unless explicitly listed as a variable:

- Dataset: `scalping_unique_games_min60_quick500.jsonl` for fast iteration
- Exploration band: `classification_ticks 20..25`, `entry_cutoff_tick 50..60`, `max_hold_ticks 7..9`
- Drift anchors under test: `P90` primary, `P75` fallback

## Toggle Axes

1. `Regime Participation`
- `ALL`
- `TREND_EXPANSION_ONLY` (`trend_up`, `expansion`)

2. `SL Strictness`
- `BASE_SL` (current SL multiplier range)
- `STRICT_SL` (lower SL range / faster downside cut)

3. `Risk Mode`
- `FLAT_STAKE`
- `REDUCED_STAKE_UNCERTAIN_CHOP`

4. `Entry Mode`
- `P1_MOMENTUM`
- `AUTO_REGIME`

## Stage Plan

### Stage A (quick ranking)

- Run all combinations above on `quick500`.
- Keep top candidates by a balanced score:
  - higher net/end SOL
  - better p10 and worst-game net
  - stable trade count (not near no-trade collapse)

### Stage B (confirmation)

- Promote top `6..10` candidates to full `min60` dataset.
- Reject candidates that collapse under small neighborhood perturbations:
  - `classification_ticks ±5`
  - `entry_cutoff_tick ±5`
  - `max_hold_ticks ±1`
  - TP/SL multiplier `±1`

### Stage C (robustness)

- Monte Carlo sequence resampling with regime reweighting stress.
- Keep only policies with positive median End SOL and acceptable downside profile.

## Candidate Promotion Rule

Promote only if all hold:

1. Positive net SOL in Stage B.
2. Non-trivial participation (avoid near-zero trade dead zones).
3. Better downside anchors than baseline (`p10_game_net_sol`, `worst_game_net_sol`).
4. No severe collapse under local perturbation tests.

## Deliverables from This Matrix

1. Ranked V1 policy shortlist with explicit toggle settings.
2. Per-policy tradeoff sheet (return vs downside).
3. Monte Carlo robustness table for promoted candidates.
4. Updated checkpoint JSON + dated markdown summary.
