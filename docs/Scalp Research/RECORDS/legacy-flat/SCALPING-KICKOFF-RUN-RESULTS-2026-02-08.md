# Scalping Kickoff Run Results (Optimization Sweep)

Date: 2026-02-08

This document records the first executed optimization cycle and extracts practical exploration ranges.

## Run Summary

Two sweeps were executed using current artifact logic (`src/artifacts/tools/scalping-explorer/main.js`):

1. Stage A + Stage B (entry-first shortlist flow)
- Stage A dataset: `scalping_unique_games_min60_quick500.jsonl`
- Stage A grid: `2,100` configs
- Stage B dataset: `scalping_unique_games_min60.jsonl` (`1,772` games)
- Stage B shortlist: top `300` configs from Stage A
- Checkpoint: `checkpoints/scalping_opt_sweep_2026-02-08.json`

2. Full-grid envelope (true global bounds)
- Dataset: `scalping_unique_games_min60.jsonl` (`1,772` games)
- Grid: all `2,100` configs on full data
- Checkpoint: `checkpoints/scalping_opt_fullgrid_envelope_2026-02-08.json`

## Best Configuration (Observed)

Best across full-grid envelope:

- `classification_ticks`: `20`
- `entry_cutoff_tick`: `55`
- `max_hold_ticks`: `9`
- `drift_reference`: `P90`
- `playbook_mode`: `P1_MOMENTUM`
- selected permutation: `TPx2 / SLx2`
- resulting TP/SL %: `+31.1235% / -37.9487%`
- trades: `5,305`
- win rate: `59.3025%`
- net SOL: `19.0780`
- end SOL (start 10): `29.0780`

## True PnL Envelope (All 2,100 Full-Grid Configs)

Net SOL distribution:

- min: `0.0000`
- p10: `0.0000`
- median: `3.5816`
- p90: `10.0028`
- max: `19.0780`

End SOL distribution (starting bankroll 10 SOL):

- min: `10.0000`
- p10: `10.0000`
- median: `13.5816`
- p90: `20.0028`
- max: `29.0780`

Additional envelope notes:

- Positive-net configs: `1,740 / 2,100` (`82.86%`)
- Zero-net configs: `360 / 2,100` (mostly no-trade restrictive settings)

## Robust Exploration Ranges (Not Single-Point Optimum)

Derived from overlap of top-profit and top-risk slices in Stage B:

- `classification_ticks`: `20..25` (center near `20`)
- `entry_cutoff_tick`: `45..60` (best concentration `55..60`)
- `max_hold_ticks`: `5..9` (best concentration `7..9`, strongest at `9`)
- `drift_reference`: mostly `P90` (with viable `P75`/`P50` alternatives)
- `playbook_mode`: mostly `P1_MOMENTUM`, secondarily `AUTO_REGIME`
- selected TP multiplier: `1..5` (dominant cluster `2..4`)
- selected SL multiplier: `2..4`

Top-50 concentration (full-grid):

- classification: `20` dominates (`36/50`)
- cutoff: `55` and `60` dominate (`34/50` combined)
- hold: `9` dominates (`28/50`), then `7` (`16/50`)
- playbook mode: `P1_MOMENTUM` (`34/50`), `AUTO_REGIME` (`16/50`)

## Entry Signal Ranking (Current Rule Set)

Best and median net SOL by playbook mode across full-grid:

- `P1_MOMENTUM`: best `19.0780`, median `6.6960`
- `AUTO_REGIME`: best `17.2277`, median `6.4190`
- `P4_BREAKOUT`: best `12.2291`, median `4.5953`
- `P2_PULLBACK_CONT`: best `8.4568`, median `2.4056`
- `P3_MEAN_REVERT`: best `8.3808`, median `1.8860`

Interpretation: momentum-led entry logic is currently the strongest optimization frontier under this simulator.

## Risk Context on Top Configs (Stage B Detailed)

For top-10 Stage B configs:

- p10 game net SOL range: `-0.0406` to `-0.0330`
- worst game net SOL range: `-0.2026` to `-0.0955`

These are useful as initial downside anchors for upcoming threshold policy design.

## Recommended Immediate Exploration Band

For the next optimization cycle, prioritize:

1. `classification_ticks`: `20..25`
2. `entry_cutoff_tick`: `50..60`
3. `max_hold_ticks`: `7..9`
4. `playbook_mode`: `P1_MOMENTUM` and `AUTO_REGIME`
5. drift anchors:
- primary: `P90`
- fallback robustness checks: `P75` and `P50`
6. TP/SL multiplier search focus:
- TP: `2..4`
- SL: `2..4`

## Post-Kickoff Addendum: V1 Simulator Snapshot

Subsequent V1 policy run on `500` games (secondary per-game window) showed:

- best per-game net: `+0.0126 SOL` (end `1.0126`)
- worst per-game net: `-0.0163 SOL` (end `0.9837`)
- positive to non-positive crossover near ranks `301..304` (`~60%` non-negative at displayed precision)
- strong rows concentrated in `trend_up`, `trend_down`, `expansion`
- higher-ranked rows largely TP/TIME dominated with low SL incidence

Implication:

- The exploration band remains valid, but policy promotion must be downside-aware because tail loss can exceed best single-game upside.

Reference:

- `SCALPING-V1-SIMULATOR-OBSERVATIONS-2026-02-08.md`
- `SCALPING-V1-TOGGLE-TEST-MATRIX.md`

## Caveat

The full-grid worst case in this run is zero-net (no trades), not negative-net. This reflects the tested parameter universe and current strategy rules, not a universal guarantee that loss-making configurations do not exist under broader rule changes.
