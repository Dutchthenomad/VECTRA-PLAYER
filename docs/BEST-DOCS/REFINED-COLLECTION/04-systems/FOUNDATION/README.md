# Foundation System

Status: in_review (Section 5)
Class: canonical
Last updated: 2026-02-12
Owner: Systems Review
Depends on: `../../01-architecture/SERVICE_BOUNDARIES.md`, `../../01-architecture/CONTRACTS/FOUNDATION_API.md`
Replaces: foundation implementation notes in source corpus

## Purpose

Describe foundation runtime behavior as ingestion, normalization, and distribution core.

## Scope

1. feed adapter integration points,
2. event normalization flow,
3. command intake baseline,
4. health/readiness and operational hooks.

## Source Inputs

1. `system-extracts/01-minimal-trading-ui-foundation.md`
2. `Statistical Opt/07-FOUNDATION-SERVICE.md`
3. `Statistical Opt/03-EVENT-SYSTEM.md`

## Canonical Decisions

1. Foundation does not own strategy logic.
2. Foundation emits canonical single-layer envelopes.
3. Foundation contract baselines are defined in architecture contracts.
