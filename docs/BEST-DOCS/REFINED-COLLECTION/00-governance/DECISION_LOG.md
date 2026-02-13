# Decision Log

Status: review-ready (Section 1)
Class: canonical
Last updated: 2026-02-12
Owner: Documentation Governance
Depends on: `DOC_STANDARDS.md`, `GLOSSARY.md`, `CONSTANTS_AND_SEMANTICS.md`
Replaces: implicit decisions scattered across source docs

## Purpose

Record explicit governance and semantic decisions with rationale and impact.

## Scope

Applies to refined documentation decisions and cross-section terminology/constants.

## Source Inputs

1. `REFINED-COLLECTION/INDEX.md`
2. `REFINED-COLLECTION/SECTION_REVIEW_QUEUE.md`
3. `REFINED-COLLECTION/PAYOUT_BREAKEVEN_SEMANTICS.md`
4. source corpus conflict scan and section mapping results

## Decision Entries

### DR-0001: Isolate Refinement Workspace

- Date: 2026-02-12
- Status: accepted
- Decision: All generated/refined artifacts live under `REFINED-COLLECTION/`.
- Rationale: Prevent contamination of source/reference corpus during restructuring.
- Impact: Source docs remain untouched while canonical docs are built in parallel.

### DR-0002: Adopt Four Document Classes

- Date: 2026-02-12
- Status: accepted
- Decision: Enforce `canonical`, `reference`, `evidence`, `legacy` classes.
- Rationale: Source corpus mixes intent; explicit classes reduce ambiguity.
- Impact: Each section/doc now has a clear authority level.

### DR-0003: Section-by-Section Review Workflow

- Date: 2026-02-12
- Status: accepted
- Decision: Review in fixed sequence (Governance -> ... -> Legacy).
- Rationale: Prevents uncontrolled rewrites and preserves dependency order.
- Impact: Work progresses as gated section closures.

### DR-0004: Dual Breakeven Semantics Are Canonical

- Date: 2026-02-12
- Status: accepted
- Decision: Preserve both valid interpretations:
  - Programmatic/settlement: `20%` (`R_total=5`)
  - Comprehensive/odds: `16.67%` (`R_profit=5`, `R_total=6`)
- Rationale: Source math supports both depending on payout definition.
- Impact: Docs must always label payout semantics explicitly.

### DR-0005: Mode Taxonomy Standardization

- Date: 2026-02-12
- Status: accepted
- Decision: Use canonical terms `live-execution`, `live-simulator`, `backtest`, `replay`, `paper-trading`.
- Rationale: Source docs use overlapping terms inconsistently.
- Impact: New docs and migrations must map old labels into this taxonomy.

### DR-0006: Source Mapping Completeness Gate

- Date: 2026-02-12
- Status: accepted
- Decision: Section migration cannot start until source map coverage is complete.
- Rationale: Avoid orphaned content during consolidation.
- Impact: Current map is complete (`147/147` source files mapped).

### DR-0007: Governance Pack 02-04 Review Baseline

- Date: 2026-02-12
- Status: accepted
- Decision: Treat `GLOSSARY.md`, `CONSTANTS_AND_SEMANTICS.md`, and this decision log as the governance baseline for cross-section refinement.
- Rationale: Section-by-section review needs a stable semantic baseline before architecture/domain consolidation.
- Impact: Later sections must align terminology and constants with this pack or explicitly request decision updates.

### DR-0008: API Payout Field Contract

- Date: 2026-02-12
- Status: accepted
- Decision: Canonical API contracts must expose payout with explicit numeric fields (`r_total` required, `r_profit` recommended), and maintain `r_total = r_profit + 1` when both are present.
- Rationale: Eliminates ambiguity caused by mixed textual interpretations of `5:1` vs `5x`.
- Impact: Architecture and domain contract docs must avoid text-only payout semantics.

### DR-0009: Service Health/Readiness Baseline

- Date: 2026-02-12
- Status: accepted
- Decision: Every service must expose `GET /health` and `GET /ready` as mandatory baseline endpoints.
- Rationale: Source extraction repeatedly identifies this as required operational baseline.
- Impact: All service contract docs and implementations must include liveness/readiness separation.

### DR-0010: Event Envelope Unification

- Date: 2026-02-12
- Status: accepted
- Decision: Canonical event delivery uses a single envelope schema (`version`, `id`, `type`, `ts`, `source`, `data`, optional `correlation_id`, optional `game_id`).
- Rationale: Source systems show wrapper variance and double-wrapping risk; unified envelope removes ambiguity.
- Impact: New services and migrations must emit one canonical envelope only.

### DR-0011: Execution Isolation

- Date: 2026-02-12
- Status: accepted
- Decision: `live-simulator` must never execute real orders; `live-execution` must be routed through a dedicated execution bridge boundary.
- Rationale: Source extraction flags real execution toggles inside simulator as architectural coupling risk.
- Impact: Any mixed-mode execution path is non-canonical and must be refactored.

## Pending Decisions

### DR-P001: Global vs Strategy-Specific Entry Zone

- Status: open
- Question: Should `tick >= 200` remain a global canonical threshold or become strategy/profile-specific?
- Owner: Strategy and Math review
- Target section: Section 4

### DR-P003: Evidence Record Schema

- Status: open
- Question: Enforce structured schema (`Context`, `Method`, `Result`, `Artifacts`) for new evidence docs?
- Owner: Governance + Evidence review
- Target section: Sections 1 and 8

## Open Questions

1. Do we need a strict versioning scheme for canonical docs (`v1`, `v1.1`) or rely on date + decision log only?
2. Should we define mandatory approver roles before a section can be marked complete?
