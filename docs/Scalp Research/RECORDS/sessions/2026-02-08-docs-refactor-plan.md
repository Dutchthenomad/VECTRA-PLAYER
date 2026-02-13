# Scalping Docs Refactor Plan

Date: 2026-02-08

## 1) Audit Summary

Current documentation footprint in `docs/SCALP TRADING RESEARCH`:

1. Markdown docs: `19` files (`2,301` lines).
2. Checkpoints: `4` JSON files.
3. Visual outputs: `8` SVG files + `figures/index.html`.

Primary issue is not missing information. It is **information architecture drift**:

1. Facts, hypotheses, plans, audits, and runbooks are mixed at the same level.
2. Key metrics are repeated in multiple files (manual sync risk).
3. Some assumptions are no longer globally true after later experiments.
4. Historical snapshots and living guidance are intermixed.

## 2) Findings (Severity Ordered)

### Critical A: Metric duplication causes high drift risk

Same session statistics are repeated across multiple docs:

1. `SCALPING-V1-SIMULATOR-OBSERVATIONS-2026-02-08.md:21`
2. `SCALPING-EMPIRICAL-FACTS.md:111`
3. `SCALPING-KICKOFF-RUN-RESULTS-2026-02-08.md:121`

Impact:

- Future edits can silently diverge numbers and narrative.

### High B: Scope statement conflict (long-only vs short experiments)

1. `SCALPING-FOUNDATIONS-ASSUMPTIONS.md:33` says long-only prototype.
2. Short-side study and validation are now active:
- `SCALPING-LONG-SHORT-EDGE-STUDY-2026-02-08.md:10`
- `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md:84`

Impact:

- New readers can misread current scope and misclassify short work status.

### High C: Planning content is fragmented across overlapping docs

Planning/execution intent appears in:

1. `SCALPING-BO-MONTE-CARLO-PLAN.md`
2. `SCALPING-KICKOFF-RUN-MATRIX.md`
3. `SCALPING-V1-TOGGLE-TEST-MATRIX.md`
4. `SCALPING-SESSION-CLOSEOUT-2026-02-08.md`

Impact:

- Difficult to identify the single active plan vs historical plan.

### Medium D: Runbooks include stale fixed-port examples

1. `SCALPING-KICKOFF-RUN-MATRIX.md:15`
2. `SCALPING-V1-SIMULATOR-RUNBOOK.md:15`
3. `SCALPING-V1-SIMULATOR-RUNBOOK.md:21`

Impact:

- Repro friction if ports are reused/unavailable.

### Medium E: Canonical vs record boundaries are weak

Operational/session-derived observations live inside canonical-style docs:

1. `SCALPING-EMPIRICAL-FACTS.md:101`
2. `SCALPING-EMPIRICAL-FACTS.md:125`

Impact:

- Harder to keep "facts" strictly reproducible from checkpoint artifacts.

## 3) Target Documentation Architecture

Refactor into two layers:

1. **Handbook (living canonical docs)**
2. **Records (dated immutable outputs)**

Proposed structure:

```text
docs/SCALP TRADING RESEARCH/
  README.md
  HANDBOOK/
    01_SCOPE_AND_ASSUMPTIONS.md
    02_DATASET_AND_PROVENANCE.md
    03_SYSTEM_MODEL_CLASSIFICATION_REGIMES.md
    04_STRATEGY_AND_FEATURE_CATALOG.md
    05_EVALUATION_PROTOCOL.md
    06_RESULTS_CANONICAL.md
    07_RISK_AND_LIMITATIONS.md
    08_ROADMAP_AND_DECISION_RULES.md
    09_OPERATIONS_RUNBOOK.md
  RECORDS/
    sessions/
    experiments/
    audits/
    checkpoints/   (pointer docs to JSON files, not duplicate metrics)
  figures/
  checkpoints/
```

## 4) Migration Map (Current -> Target)

### Keep as living handbook source (consolidate content)

1. `SCALPING-FOUNDATIONS-ASSUMPTIONS.md` -> `HANDBOOK/01_SCOPE_AND_ASSUMPTIONS.md`
2. `SCALPING-DATASET-COLLECTION-REPORT.md` -> `HANDBOOK/02_DATASET_AND_PROVENANCE.md`
3. `SCALPING-CLASSIFICATION-AND-REGIME-PRIMER.md` -> `HANDBOOK/03_SYSTEM_MODEL_CLASSIFICATION_REGIMES.md`
4. `SCALPING-TA-TOOLKIT-BRAINSTORM.md` + trigger catalog parts -> `HANDBOOK/04_STRATEGY_AND_FEATURE_CATALOG.md`
5. `SCALPING-BO-MONTE-CARLO-PLAN.md` + promotion criteria from matrices -> `HANDBOOK/05_EVALUATION_PROTOCOL.md`
6. `SCALPING-EMPIRICAL-FACTS.md` (strict reproducible sections only) -> `HANDBOOK/06_RESULTS_CANONICAL.md`
7. limitations content from audits/closeout -> `HANDBOOK/07_RISK_AND_LIMITATIONS.md`
8. `SCALPING-THEORETICAL-AVENUES.md` + active priorities from closeout -> `HANDBOOK/08_ROADMAP_AND_DECISION_RULES.md`
9. `SCALPING-EXPLORER-RUNBOOK.md` + `SCALPING-V1-SIMULATOR-RUNBOOK.md` -> `HANDBOOK/09_OPERATIONS_RUNBOOK.md`

### Move to records (immutable historical docs)

1. `SCALPING-KICKOFF-RUN-MATRIX.md` -> `RECORDS/experiments/2026-02-08-kickoff-run-matrix.md`
2. `SCALPING-KICKOFF-RUN-RESULTS-2026-02-08.md` -> `RECORDS/experiments/2026-02-08-kickoff-run-results.md`
3. `SCALPING-V1-TOGGLE-TEST-MATRIX.md` -> `RECORDS/experiments/2026-02-08-v1-toggle-test-matrix.md`
4. `SCALPING-V1-SIMULATOR-OBSERVATIONS-2026-02-08.md` -> `RECORDS/experiments/2026-02-08-v1-observations.md`
5. `SCALPING-LONG-SHORT-EDGE-STUDY-2026-02-08.md` -> `RECORDS/experiments/2026-02-08-long-short-edge-study.md`
6. `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md` -> `RECORDS/experiments/2026-02-08-trigger-variants-validation.md`
7. `SCALPING-SESSION-CLOSEOUT-2026-02-08.md` -> `RECORDS/sessions/2026-02-08-session-closeout.md`
8. `SCALPING-COMPREHENSIVE-AUDIT-2026-02-08.md` -> `RECORDS/audits/2026-02-08-comprehensive-audit.md`
9. `SCALPING-V2-PIPELINE-CONTEXT-AUDIT-2026-02-08.md` -> `RECORDS/audits/2026-02-08-v2-pipeline-context-audit.md`

## 5) Canonical Data Ownership Rule

Single-source rule after refactor:

1. All canonical metrics live in `HANDBOOK/06_RESULTS_CANONICAL.md`.
2. Dated experiment docs can include metrics but must be treated as historical outputs.
3. Any repeated metric in roadmap/audit docs must link back to the canonical source section.

## 6) Refactor Execution Plan

### Phase 1: Skeleton + Indexing

1. Create `HANDBOOK/` and `RECORDS/` directories.
2. Update `README.md` with two top-level navigation tables:
- Handbook (living),
- Records (dated).
3. Add explicit status tags per doc:
- `status: active|archived|superseded`.

### Phase 2: Consolidate living docs

1. Merge overlapping planning docs into one evaluation protocol.
2. Merge runbooks into one operations runbook with separate sections per artifact.
3. Remove non-canonical operational anecdotes from empirical facts.
4. Resolve assumption conflicts (long-only -> long-primary with short-sandbox note).

### Phase 3: Normalize records

1. Move dated docs to `RECORDS/` paths.
2. Keep content mostly unchanged (immutability).
3. Add lightweight frontmatter to each record:
- date,
- dataset,
- code/artifact version references,
- status.

### Phase 4: Integrity pass

1. Replace duplicated numbers in handbook docs with references to canonical results section.
2. Ensure each factual claim has trace path to:
- checkpoint JSON,
- experiment record,
- or source doc.
3. Add "Last validated" line to each handbook doc.

## 7) Definition of Done

Refactor is complete when:

1. A new reader can answer "what is true now" from handbook only.
2. Historical detail is discoverable without polluting canonical docs.
3. No key metric appears as canonical in more than one living doc.
4. Scope assumptions and strategy status are internally consistent.
5. README navigation makes the lifecycle explicit: model -> method -> results -> risks -> roadmap -> operations.

## 8) Recommended Work Packages (PR-sized)

1. PR-A: Structure and index only (`HANDBOOK/`, `RECORDS/`, README navigation).
2. PR-B: Living-doc consolidations (method/results/ops/roadmap).
3. PR-C: Historical migration + cross-link cleanup + final consistency pass.
