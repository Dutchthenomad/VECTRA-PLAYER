# Strategy Profile Generation

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `MONTE_CARLO.md`, `../RISK/POSITION_SIZING.md`, `../PROBABILITY/SURVIVAL_MODEL.md`
Replaces: profile generation notes from optimization integration docs

## Purpose

Define canonical strategy profile artifact built from probability, risk, and simulation outputs.

## Scope

1. Profile fields.
2. Generation pipeline.
3. Quality gates.

## Source Inputs

1. `STATISTICAL-OPTIMIZATION-INTEGRATION.md`
2. `system-extracts/05-monte-carlo-comparison.md`
3. `Statistical Opt/EXPLORER-TAB/08-STRATEGY-ANALYSIS.md`

## Canonical Decisions

### 1) Profile Minimum Fields

- `profile_id`
- `data_version`
- `assumption_set`
- `recommended_entry_policy`
- `sizing_policy`
- `risk_summary`
- `confidence_notes`

### 2) Generation Pipeline

1. probability baseline
2. risk sizing + controls
3. Monte Carlo robustness
4. profile synthesis with rationale

### 3) Governance Rule

Profiles are outputs, not immutable canon; promotion to operational baseline requires operations-section signoff.

## Open Questions

1. Should profile ranking be scalar or multi-objective with explicit Pareto frontier reporting?
