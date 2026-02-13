# Checkpoint Catalog (2026-02-08)

Status: active
Last updated: 2026-02-08

Canonical checkpoint files live in `../../checkpoints/`.

## Files

1. `../../checkpoints/scalping_empirical_checkpoint_2026-02-08.json`
- Empirical distribution and touch-rate anchors from canonical `min60`.

2. `../../checkpoints/scalping_tp_sl_timeexit_checkpoint_2026-02-08.json`
- Time-backstopped TP/SL grid outcomes.

3. `../../checkpoints/scalping_opt_sweep_2026-02-08.json`
- Stage A/B shortlist sweep output.

4. `../../checkpoints/scalping_opt_fullgrid_envelope_2026-02-08.json`
- Full 2,100-config envelope output.

## Usage Rule

1. Do not edit checkpoint JSON by hand.
2. Publish new runs as new dated files.
3. Update `HANDBOOK/06_RESULTS_CANONICAL.md` only after validation.
