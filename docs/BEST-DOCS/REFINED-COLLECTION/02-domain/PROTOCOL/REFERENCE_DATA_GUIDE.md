# Reference Data Guide

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `RUGS_WS_PROTOCOL.md`, `../../07-evidence/DATASETS/README.md`
Replaces: `rosetta-stone/reference-data/README.md`

## Purpose

Define how protocol reference datasets are cataloged, validated, and consumed during refinement and implementation.

## Scope

1. Reference capture inventory.
2. Provenance requirements.
3. Validation and usage rules.

## Source Inputs

1. `rosetta-stone/reference-data/README.md`
2. `rosetta-stone/reference-data/game-20260206-003482fbeaae4ad5-full.json`
3. `rosetta-stone/reference-data/key-samples.json`

## Canonical Decisions

### 1) Required Provenance Metadata

Every reference dataset must include:

1. capture timestamp,
2. capture method/source service,
3. event coverage statement,
4. schema/version expectation.

### 2) Reference Dataset Roles

1. Full captures: regression and parser validation.
2. Curated samples: field semantics examples and unit tests.
3. Aggregated summaries: documentation-level quick checks.

### 3) Validation Rules

1. New parser/event-schema changes must replay against full captures.
2. Curated sample checks must pass before schema updates are accepted.
3. Dataset hash/version must be recorded in evidence records for reproducibility.

## Open Questions

1. Should we publish immutable dataset IDs (content hash) in all canonical docs that reference data?
