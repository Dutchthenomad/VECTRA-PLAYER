# Data Model

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `CANONICAL_DATASETS.md`, `FEATURE_DICTIONARY.md`, `../../01-architecture/CONTRACTS/EVENT_SCHEMAS.md`
Replaces: dataset/feature definitions spread across ML/risk docs

## Purpose

Define canonical dataset entities and feature vocabulary consumed by strategy and system modules.

## Scope

1. Dataset taxonomy and required metadata.
2. Feature definitions and naming conventions.
3. Cross-section consistency between protocol, strategy, and services.

## Canonical Decisions

1. Dataset and feature docs are canonical interface layers between domain and strategy sections.
2. Feature names should be stable and snake_case unless protocol compatibility requires otherwise.
3. Every feature must define units, derivation source, and data type.
