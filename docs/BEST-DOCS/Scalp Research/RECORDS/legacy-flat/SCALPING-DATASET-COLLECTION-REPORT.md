# Scalping Dataset Collection Report

Date: 2026-02-08

## Objective

Find the best source of unique individual game recordings with full tick-by-tick price arrays and prepare simulator-ready files for the scalping explorer artifact.

## Source Audit

### Source A: `/home/devops/rugs_recordings`

- Files scanned: 10
- Unique game IDs recovered: 39
- Games with `prices.length >= 60`: 25
- Observation: Very large files but heavy repetition of the same games from repeated `gameHistory` snapshots.

### Source B: `/home/devops/rugs_data/events_parquet/doc_type=complete_game`

- Raw rows: 12,786
- Unique game IDs: 2,530
- Best deduped rows with `prices.length >= 60`: 1,772
- Observation: Highest coverage and best unique game variety.

## Decision

Use **Source B** as canonical for scalping strategy exploration.

## Prepared Collections (Simulator-Ready JSONL)

Location: `/home/devops/rugs_data/exports/scalping_explorer`

1. `scalping_unique_games_min60_quick500.jsonl`
- 500 unique games
- Recommended for fast iteration
- Fully compatible with explorer default `Min Game Length = 60`

2. `scalping_unique_games_min60.jsonl`
- 1,772 unique games
- Recommended for broader backtesting/exploration

3. Also available (less strict):
- `scalping_unique_games_min30_quick500.jsonl`
- `scalping_unique_games_min30.jsonl`

## Validation Results

Both `min60` files were loaded and run in the artifact successfully:

- 500-file: `500 unique games loaded`, run completed on 500 games.
- 1,772-file: `1772 unique games loaded`, run completed (default cap 500).

## Rebuild Command

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE
./.venv/bin/python scripts/build_scalping_dataset.py --min-len 60 --quick-size 500
```
