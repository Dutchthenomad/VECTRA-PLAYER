# 02 Dataset and Provenance

Status: active
Last validated: 2026-02-08

## Objective

Document canonical dataset sources, preparation logic, and reproducibility paths.

## Source Audit Summary

1. `/home/devops/rugs_recordings`
- Large raw files, but heavy repetition in `gameHistory` snapshots.
- Limited unique usable complete games for this study.

2. `/home/devops/rugs_data/events_parquet/doc_type=complete_game`
- Best unique coverage and consistency.
- Selected as canonical source for current research corpus.

## Canonical Exports

Location:

- `/home/devops/rugs_data/exports/scalping_explorer`

Primary files:

1. `scalping_unique_games_min60.jsonl` (`1,772` games)
2. `scalping_unique_games_min60_quick500.jsonl` (`500` games)
3. `scalping_unique_games_min30.jsonl` (`2,056` games)
4. `scalping_unique_games_min30_quick500.jsonl` (`500` games)

## Recommended Use

1. Fast iteration: `min60_quick500`
2. Canonical validation: `min60`
3. Larger-pass stress check: `min30`

## Rebuild Command

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE
./.venv/bin/python scripts/build_scalping_dataset.py --min-len 60 --quick-size 500
```

## Known Sampling Limitation

Current quick set construction has known time-bias risk if generated from latest-first ordering.
For promotion-grade runs, prefer stratified sampling by date/regime and store a manifest of selected game IDs.

## Provenance References

1. Dataset collection record:
- `../RECORDS/experiments/2026-02-08-kickoff-run-matrix.md` (execution baseline context)
- `../RECORDS/legacy-flat/SCALPING-DATASET-COLLECTION-REPORT.md` (original full report)

2. Checkpoint references:
- `../checkpoints/scalping_empirical_checkpoint_2026-02-08.json`
- `../checkpoints/scalping_opt_sweep_2026-02-08.json`
- `../checkpoints/scalping_opt_fullgrid_envelope_2026-02-08.json`
