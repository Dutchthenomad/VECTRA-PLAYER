# Scalp Research (Refactored)

Status: active
Last updated: 2026-02-08

This is the refactored, replacement-ready documentation set for scalping research.
It is split into:

1. `HANDBOOK/` for living canonical guidance.
2. `RECORDS/` for dated immutable outputs.
3. `figures/` and `checkpoints/` for reproducibility artifacts.

## Quick Start

Read in this order:

1. `HANDBOOK/01_SCOPE_AND_ASSUMPTIONS.md`
2. `HANDBOOK/03_SYSTEM_MODEL_CLASSIFICATION_REGIMES.md`
3. `HANDBOOK/05_EVALUATION_PROTOCOL.md`
4. `HANDBOOK/06_RESULTS_CANONICAL.md`
5. `HANDBOOK/08_ROADMAP_AND_DECISION_RULES.md`
6. `HANDBOOK/09_OPERATIONS_RUNBOOK.md`

## Handbook (Living Canonical)

1. `HANDBOOK/01_SCOPE_AND_ASSUMPTIONS.md`
2. `HANDBOOK/02_DATASET_AND_PROVENANCE.md`
3. `HANDBOOK/03_SYSTEM_MODEL_CLASSIFICATION_REGIMES.md`
4. `HANDBOOK/04_STRATEGY_AND_FEATURE_CATALOG.md`
5. `HANDBOOK/05_EVALUATION_PROTOCOL.md`
6. `HANDBOOK/06_RESULTS_CANONICAL.md`
7. `HANDBOOK/07_RISK_AND_LIMITATIONS.md`
8. `HANDBOOK/08_ROADMAP_AND_DECISION_RULES.md`
9. `HANDBOOK/09_OPERATIONS_RUNBOOK.md`

## Records (Dated, Immutable)

1. `RECORDS/sessions/`
2. `RECORDS/experiments/`
3. `RECORDS/audits/`
4. `RECORDS/checkpoints/`
5. `RECORDS/legacy-flat/` (full snapshot of prior flat `.md` docs for rollback safety)

## Artifact Assets

1. `figures/index.html` and `figures/*.svg`
2. `checkpoints/*.json`

## Governance Rules

1. Canonical claims go only into `HANDBOOK/`.
2. Dated run outputs go only into `RECORDS/`.
3. Metrics that are considered "current truth" must live in `HANDBOOK/06_RESULTS_CANONICAL.md`.
4. If a dated record conflicts with canonical guidance, canonical guidance wins until revalidated.
