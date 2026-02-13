# Domain

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `../00-governance/GLOSSARY.md`, `../00-governance/CONSTANTS_AND_SEMANTICS.md`, `../01-architecture/EVENT_MODEL.md`
Replaces: domain rules spread across protocol, trading, and analysis docs

## Purpose

Define the canonical domain model: protocol semantics, market/trading rules, and dataset/feature shape used by strategy and systems layers.

## Scope

1. Protocol semantics and phase model.
2. Trading and sidebet mechanics.
3. Canonical datasets and feature definitions.

## Contents

1. `PROTOCOL/README.md`
2. `PROTOCOL/RUGS_WS_PROTOCOL.md`
3. `PROTOCOL/REFERENCE_DATA_GUIDE.md`
4. `TRADING/README.md`
5. `TRADING/MARKET_MECHANICS.md`
6. `TRADING/POSITION_AND_SIDEBET_RULES.md`
7. `DATA_MODEL/README.md`
8. `DATA_MODEL/CANONICAL_DATASETS.md`
9. `DATA_MODEL/FEATURE_DICTIONARY.md`

## Primary Source Inputs

1. `rosetta-stone/ROSETTA-STONE.md`
2. `rosetta-stone/reference-data/README.md`
3. `PRNG CRACKING RESEARCH/PRNG-QUICK-REFERENCE.md`
4. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
5. `Machine Learning/models/sidebet-v1/training_data/README.md`
6. `risk_management/README.md`

## Canonical Decisions

1. Domain definitions are source-of-truth inputs to strategy/system docs.
2. All payout and breakeven statements follow `R_total`/`R_profit` semantics.
3. Protocol-observed facts and modeling defaults are labeled separately.

## Open Questions

1. Should authenticated/private websocket events be split into a separate protocol volume once fully mapped?
2. Should `x_payout` be modeled as dynamic domain field or constrained enum in v1 data model?
