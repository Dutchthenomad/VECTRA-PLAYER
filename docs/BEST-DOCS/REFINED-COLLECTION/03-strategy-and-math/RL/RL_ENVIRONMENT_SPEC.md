# RL Environment Spec

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `OBSERVATION_ACTION_REWARD.md`, `../../02-domain/DATA_MODEL/CANONICAL_DATASETS.md`
Replaces: RL environment notes in source corpus

## Purpose

Define canonical environment interface for RL training and evaluation.

## Scope

1. Episode lifecycle.
2. Step/reset interface semantics.
3. Determinism and dataset coupling requirements.

## Source Inputs

1. `Statistical Opt/RL-TRAINING/19-SIDEBET-RL-ENVIRONMENT.md`
2. `Machine Learning/models/sidebet-v1/design/ENVIRONMENT_v1.md`
3. `Machine Learning/models/sidebet-v1/training_data/README.md`

## Canonical Decisions

### 1) Episode Model

One episode corresponds to one game/round lifecycle from initial state to termination.

### 2) Environment Interface

1. `reset(seed, dataset_ref)` returns initial observation and metadata.
2. `step(action)` returns next observation, reward, terminated, truncated, info.
3. info payload must include mode/context metadata for auditability.

### 3) Determinism Rule

For same seed + dataset slice + config, backtest RL rollouts should be reproducible.

### 4) Guard Rule

Environment enforces domain constraints (e.g., invalid action windows become deterministic no-ops or penalties per spec).

## Open Questions

1. Should invalid actions be auto-converted, masked, or hard-failed in canonical v1?
