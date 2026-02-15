# Protocol

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `RUGS_WS_PROTOCOL.md`, `REFERENCE_DATA_GUIDE.md`, `../../01-architecture/CONTRACTS/EVENT_SCHEMAS.md`
Replaces: protocol descriptions spread across source docs

## Purpose

Define canonical protocol semantics consumed by foundation and downstream services.

## Scope

1. Event and phase semantics.
2. Field-level meaning and units.
3. Reference capture provenance.

## Canonical Decisions

1. Public feed semantics are canonical baseline for v1 ingestion.
2. Event normalization rules live in architecture contracts; protocol docs define raw meaning only.
3. Every protocol claim must be traceable to captured reference data.

## Open Questions

1. Should protocol docs publish compatibility tiers (`public-only`, `authenticated`, `admin`) now or after full auth-event extraction?
