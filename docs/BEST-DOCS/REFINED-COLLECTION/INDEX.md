# Refined Collection Control Center

Status: active
Last updated: 2026-02-12
Scope: coordination hub for progressive documentation refinement

## Mission

Refine the existing BEST-DOCS reference corpus into a unified next-iteration documentation system, reviewed together one section at a time.

## Working Rules

1. Do not modify source/reference files during mapping and review.
2. Build canonical docs inside `REFINED-COLLECTION/` first.
3. Treat every migration as traceable: `source -> target slot -> final canonical doc`.
4. Review in section order and close each section before starting the next.

## Review Sequence

| Order | Section | Status | Primary Working Path |
|---|---|---|---|
| 1 | Governance | complete | `00-governance/` |
| 2 | Architecture | in_review | `01-architecture/` |
| 3 | Domain | in_review | `02-domain/` |
| 4 | Strategy and Math | in_review | `03-strategy-and-math/` |
| 5 | Systems | in_review | `04-systems/` |
| 6 | Operations | in_review | `05-operations/` |
| 7 | Research | in_review | `06-research/` |
| 8 | Evidence | in_review | `07-evidence/` |
| 9 | Legacy | in_review | `08-legacy/` |

## Key Artifacts

- Structure blueprint: `SORTING_LAYOUT_BLUEPRINT.md`
- Source-to-target map: `MIGRATION_MAP.md`
- Section review queue: `SECTION_REVIEW_QUEUE.md`
- Full source manifest snapshot: `FILE_MANIFEST.md`
- Refined workspace manifest: `REFINED_FILE_MANIFEST.md`
- Payout semantics canon: `PAYOUT_BREAKEVEN_SEMANTICS.md`

## Current Phase

Phase: `Review wave active: Sections 2-9 in_review`

### Ready Checklist

- [x] Target directory skeleton exists
- [x] Section README stubs exist
- [x] Canonical spine stubs exist
- [x] Initial source-to-target map exists
- [x] Section 1 (Governance) reviewed together
- [ ] Section 2 (Architecture) reviewed together
- [ ] Section 3 (Domain) reviewed together
- [ ] Section 4 (Strategy and Math) reviewed together
- [ ] Section 5 (Systems) reviewed together
- [ ] Section 6 (Operations) reviewed together
- [ ] Section 7 (Research) reviewed together
- [ ] Section 8 (Evidence) reviewed together
- [ ] Section 9 (Legacy) reviewed together

## Next Action

Run collaborative review section-by-section, beginning with Section 2 in `01-architecture/`, then proceeding through Sections 3-9 in queue order.
