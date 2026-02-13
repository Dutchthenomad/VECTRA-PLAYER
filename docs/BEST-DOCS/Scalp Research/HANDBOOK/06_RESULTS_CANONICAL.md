# 06 Results Canonical

Status: active
Last validated: 2026-02-08

This file is the single canonical location for current validated metrics.

## Data Baseline

1. Canonical set: `scalping_unique_games_min60.jsonl` (`1,772` games).
2. Larger-pass set: `scalping_unique_games_min30.jsonl` (`2,056` games).

## A) Empirical Envelope Facts (min60)

Reference checkpoint:

- `../checkpoints/scalping_empirical_checkpoint_2026-02-08.json`

5-tick return envelope:

1. mean: `1.8502%`
2. median: `2.1902%`
3. p10 / p90: `-20.0888% / 23.7247%`

5-tick excursion anchors:

1. MAE p50: `-1.0696%`
2. MAE p10: `-21.7930%`
3. MFE p50 / p75 / p90: `3.7411% / 10.7467% / 24.8136%`

## B) TP/SL First-Touch and Time-Backstopped Grid (min60)

Reference checkpoint:

- `../checkpoints/scalping_tp_sl_timeexit_checkpoint_2026-02-08.json`

Selected first-touch snapshot (5 ticks):

1. `SL -4 / TP +6`:
- TP first `34.4229%`
- SL first `26.1740%`
- neither `39.4032%`

Time-backstopped mean return examples:

1. `-4 / +6`: `1.6908%`
2. `-6 / +8`: `1.7555%`
3. `-12 / +15`: `1.9939%`

## C) Optimization Sweep Envelope (min60)

References:

1. `../checkpoints/scalping_opt_sweep_2026-02-08.json`
2. `../checkpoints/scalping_opt_fullgrid_envelope_2026-02-08.json`

Full-grid (`2,100` configs) net SOL summary:

1. min / p10 / median / p90 / max:
- `0.0000 / 0.0000 / 3.5816 / 10.0028 / 19.0780`
2. positive-net configs:
- `1,740 / 2,100` (`82.86%`)
3. zero-net configs:
- `360 / 2,100`

## D) Trigger Variant Validation (One-Trade-Per-Game)

Reference record:

- `../RECORDS/experiments/2026-02-08-trigger-variants-validation.md`

Current tentative primary candidate:

1. `HOS_V1_SCORE_ROUTED` on `min60`:
- `n=1,054`, win `68.8%`, mean/median `+2.66% / +3.16%`
2. `HOS_V1_SCORE_ROUTED` on `min30`:
- `n=1,080`, win `68.9%`, mean/median `+2.63% / +3.19%`

Short-side note:

1. `S1_BLOWOFF_STRICT_SHORT` remains experimental; split stability is insufficient for primary promotion.

## E) Canonical Interpretation (Current)

1. Strongest validated edge family is long-side, expansion/rebound-oriented, with score-routed gating.
2. Short-side opportunities exist as hypotheses but are not stable enough for primary policy.
3. Robustness and downside governance remain mandatory before production claims.

## Non-Canonical Operational Notes

Session-level UI observations (for example single run table rank patterns) belong in dated records, not in this file.

See:

1. `../RECORDS/experiments/2026-02-08-v1-observations.md`
2. `../RECORDS/sessions/2026-02-08-session-closeout.md`
