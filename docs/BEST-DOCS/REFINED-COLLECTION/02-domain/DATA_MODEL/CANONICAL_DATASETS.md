# Canonical Datasets

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `FEATURE_DICTIONARY.md`, `../../07-evidence/DATASETS/README.md`
Replaces: dataset inventory fragments in source corpus

## Purpose

Establish canonical dataset classes and metadata requirements.

## Scope

1. Event-level datasets.
2. Round/game summary datasets.
3. Sidebet/strategy outcome datasets.

## Source Inputs

1. `Machine Learning/models/sidebet-v1/training_data/README.md`
2. `rosetta-stone/reference-data/README.md`
3. `Scalp Research/checkpoints/*.json`
4. `risk_management/*.py` references

## Canonical Decisions

### 1) Dataset Classes

1. `event_stream` (raw/normalized event-level records)
2. `game_summary` (per-round derived facts)
3. `trade_outcomes` (position/sidebet outcome records)
4. `strategy_runs` (simulation/backtest run outputs)

### 2) Required Dataset Metadata

1. dataset id/name
2. source and capture/build method
3. schema version
4. timeframe and sample count
5. lineage (input datasets)

### 3) Canonical Field Categories

1. identity fields (`game_id`, `session_id`, `event_id`)
2. temporal fields (`tick`, `timestamp_ms`)
3. value fields (`price`, `qty`, `pnl`)
4. semantic flags (`active`, `rugged`, `is_unplayable`)

## Open Questions

1. Should we require semantic versioning for all dataset schemas before Section 5 system implementation pass?
