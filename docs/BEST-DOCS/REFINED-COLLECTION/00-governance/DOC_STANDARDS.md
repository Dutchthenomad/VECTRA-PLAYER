# Documentation Standards

Status: complete (Section 1)
Class: canonical
Last updated: 2026-02-12
Owner: Documentation Governance
Depends on: `GLOSSARY.md`, `CONSTANTS_AND_SEMANTICS.md`, `../INDEX.md`
Replaces: ad hoc standards across source docs

## Purpose

Define the required structure, metadata, naming, and evidence rules for all documentation in `REFINED-COLLECTION/`.

## Scope

Applies to all files in:

- `00-governance` to `08-legacy`
- all future canonical docs migrated from source corpus

## Source Inputs

1. `system-extracts/README.md`
2. `Scalp Research/README.md`
3. `Scalp Research/HANDBOOK/README.md`
4. `Scalp Research/RECORDS/README.md`
5. `rosetta-stone/ROSETTA-STONE.md`
6. `REFINED-COLLECTION/SORTING_LAYOUT_BLUEPRINT.md`
7. `REFINED-COLLECTION/PAYOUT_BREAKEVEN_SEMANTICS.md`

## Canonical Decisions

### 1) Document Classes

Every document must be one of:

1. `canonical`: normative build guidance and contracts.
2. `reference`: explanatory support, implementation notes, background.
3. `evidence`: dated records, outputs, checkpoints, artifacts.
4. `legacy`: historical snapshots retained for traceability.

### 2) Required Metadata Header

Every non-evidence doc must contain these fields at top:

```text
Status:
Class:
Last updated:
Owner:
Depends on:
Replaces:
```

For `evidence` docs, `Replaces` may be omitted.

### 3) Naming Rules

1. Canonical and reference docs use stable names without dates.
2. Evidence docs must include ISO date prefix (`YYYY-MM-DD-*`) where practical.
3. Legacy docs preserve original filenames.
4. Folder ordering remains numeric (`00-` through `08-`).

### 4) Source Traceability Rule

All canonical docs must include a `Source Inputs` section listing source files used to derive decisions.

### 5) Canonical Claims Rule

A statement is canonical only if it appears in a canonical doc under:

- `Canonical Decisions`, or
- an explicit constants table in `CONSTANTS_AND_SEMANTICS.md`.

If source files conflict, the canonical doc must:

1. state the conflict,
2. define the selected interpretation,
3. log the decision in `DECISION_LOG.md`.

### 6) Semantics and Constants Rule

1. Use terms exactly as defined in `GLOSSARY.md`.
2. Use constants exactly as defined in `CONSTANTS_AND_SEMANTICS.md`.
3. Never use `5:1` or `5x` without declaring whether it is total return or net odds.

### 7) Mode Taxonomy Rule

All runtime/docs language must use the canonical mode taxonomy:

- `live-execution`
- `live-simulator`
- `backtest`
- `replay`
- `paper-trading`

Definitions are in `GLOSSARY.md`.

### 8) Evidence Immutability Rule

Files under `07-evidence/` are append-only historical records. Corrections are added as new dated records, not destructive edits.

### 9) Review and Closure Rule

Section closure requires:

1. section docs drafted,
2. open questions captured,
3. at least one decision-log entry if conflicts existed,
4. section status updated in `SECTION_REVIEW_QUEUE.md`.

## Canonical Template

Use this baseline for new canonical docs:

```markdown
# <Title>

Status: complete (Section 1)
Class: canonical
Last updated: YYYY-MM-DD
Owner: <team/role>
Depends on: <doc paths>
Replaces: <source doc paths or none>

## Purpose

## Scope

## Source Inputs

## Canonical Decisions

## Open Questions
```

## Open Questions

1. Do we want an explicit `Reviewed by` metadata field at top-level?
2. Should evidence docs require a stricter schema (`Context`, `Method`, `Result`, `Artifacts`)?
