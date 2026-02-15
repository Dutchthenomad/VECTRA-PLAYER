# ML Pipelines

Status: in_review (Section 5)
Class: canonical
Last updated: 2026-02-12
Owner: Systems Review
Depends on: `../../03-strategy-and-math/RL/README.md`, `../../02-domain/DATA_MODEL/CANONICAL_DATASETS.md`
Replaces: ML pipeline implementation plan docs in source corpus

## Purpose

Define pipeline-system documentation for dataset preparation, training generation, and model artifact production.

## Scope

1. dataset extraction and normalization,
2. training tuple generation,
3. model artifact lifecycle,
4. reproducibility and version lineage.

## Source Inputs

1. `2025-12-28-pipeline-d-training-data-implementation.md`
2. `Machine Learning/models/sidebet-v1/*`
3. `Machine Learning/README.md`

## Canonical Decisions

1. Pipeline steps are explicitly versioned and traceable.
2. Training artifacts must reference input dataset and feature dictionary versions.
3. Pipeline docs define flow and contract, not algorithm internals.
