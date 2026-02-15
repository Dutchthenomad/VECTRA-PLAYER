# Unified Documentation Sorting Layout Blueprint

Last updated: 2026-02-12
Status: proposed canonical layout for next-iteration docs

## 1) Objective

Create a stable documentation structure that separates:

1. Current truth used to build the next application.
2. Supporting technical references.
3. Research evidence and experiment history.
4. Legacy material retained for traceability.

## 2) Core Sorting Model

Every document is assigned one class:

1. `canonical`: normative source of truth.
2. `reference`: explanatory or supporting material.
3. `evidence`: dated outputs, audits, experiment records.
4. `legacy`: historical snapshots not used as active guidance.

## 3) Target Top-Level Layout

```text
BEST-DOCS/
  00-governance/
    README.md
    GLOSSARY.md
    CONSTANTS_AND_SEMANTICS.md
    DOC_STANDARDS.md
    DECISION_LOG.md

  01-architecture/
    README.md
    SYSTEM_OVERVIEW.md
    SERVICE_BOUNDARIES.md
    EVENT_MODEL.md
    MODES_AND_EXECUTION_MODEL.md
    CONTRACTS/
      FOUNDATION_API.md
      EVENT_SCHEMAS.md

  02-domain/
    README.md
    PROTOCOL/
      RUGS_WS_PROTOCOL.md
      REFERENCE_DATA_GUIDE.md
    TRADING/
      MARKET_MECHANICS.md
      POSITION_AND_SIDEBET_RULES.md
    DATA_MODEL/
      CANONICAL_DATASETS.md
      FEATURE_DICTIONARY.md

  03-strategy-and-math/
    README.md
    PROBABILITY/
      SURVIVAL_MODEL.md
      BAYESIAN_RUG_SIGNAL.md
    RISK/
      POSITION_SIZING.md
      DRAWDOWN_CONTROL.md
      RISK_METRICS.md
    OPTIMIZATION/
      MONTE_CARLO.md
      STRATEGY_PROFILE_GENERATION.md
    RL/
      RL_ENVIRONMENT_SPEC.md
      OBSERVATION_ACTION_REWARD.md

  04-systems/
    README.md
    FOUNDATION/
    EXPLORER/
    BACKTEST/
    LIVE_SIMULATOR/
    ML_PIPELINES/

  05-operations/
    README.md
    RUNBOOKS/
    DEPLOYMENT/
    TESTING_AND_VALIDATION/
    MONITORING/

  06-research/
    README.md
    SCALPING/
      HANDBOOK/
    PRNG/
    INVESTIGATIONS/

  07-evidence/
    README.md
    SESSIONS/
    EXPERIMENTS/
    AUDITS/
    CHECKPOINTS/
    FIGURES/
    DATASETS/

  08-legacy/
    README.md
    FLAT_SNAPSHOTS/
    ARCHIVE_DOCS/
    PROTOTYPES/
```

## 4) Mapping from Current Structure

| Current | Target | Class | Notes |
|---|---|---|---|
| `system-extracts/` | `01-architecture/` and `04-systems/` | canonical | Primary rebuild source. Split concepts vs module specifics. |
| `Scalp Research/HANDBOOK/` | `06-research/SCALPING/HANDBOOK/` | canonical/reference | Keep as living research canon. |
| `Scalp Research/RECORDS/` | `07-evidence/` | evidence | Preserve dated immutable outputs. |
| `Scalp Research/figures/` | `07-evidence/FIGURES/` | evidence | Keep reproducibility assets together. |
| `Scalp Research/checkpoints/` | `07-evidence/CHECKPOINTS/` | evidence | Keep checkpoint JSON with catalog docs. |
| `Statistical Opt/` | `03-strategy-and-math/` + `04-systems/` | reference/canonical candidate | Extract reusable canonical modules; retain detailed pages as reference. |
| `Machine Learning/` | `03-strategy-and-math/RL/` + `04-systems/ML_PIPELINES/` | canonical/reference | Split theory/spec from implementation/process docs. |
| `risk_management/` | `03-strategy-and-math/RISK/` | canonical/reference | Promote formulas and state machine; keep scripts as implementation refs. |
| `rosetta-stone/` | `02-domain/PROTOCOL/` + `07-evidence/DATASETS/` | canonical + evidence | Protocol doc canonical; large JSON stays evidence. |
| `PRNG CRACKING RESEARCH/` | `06-research/PRNG/` | reference/evidence | Keep specialized track isolated from core architecture. |
| `bayesian prediction engine/` | `08-legacy/PROTOTYPES/` + extracted pieces to `03-strategy-and-math/PROBABILITY/` | legacy + canonical extraction | Treat as prototype source, not active architecture. |
| `specs/` | `01-architecture/CONTRACTS/` | canonical | Use as contract seed set. |
| root overview docs | `00-governance/`, `01-architecture/`, `03-strategy-and-math/` | mixed | Normalize and redistribute by intent. |

## 5) Canonical Spine (Build Order)

This is the minimum ordered spine for a new engineer:

1. `00-governance/README.md`
2. `00-governance/GLOSSARY.md`
3. `00-governance/CONSTANTS_AND_SEMANTICS.md`
4. `01-architecture/SYSTEM_OVERVIEW.md`
5. `01-architecture/MODES_AND_EXECUTION_MODEL.md`
6. `01-architecture/CONTRACTS/FOUNDATION_API.md`
7. `02-domain/PROTOCOL/RUGS_WS_PROTOCOL.md`
8. `03-strategy-and-math/PROBABILITY/SURVIVAL_MODEL.md`
9. `03-strategy-and-math/RISK/POSITION_SIZING.md`
10. `03-strategy-and-math/RL/RL_ENVIRONMENT_SPEC.md`
11. `04-systems/README.md`
12. `05-operations/RUNBOOKS/`

## 6) Sorting and Naming Rules

1. Folder ordering uses numeric prefixes (`00` to `08`) to force stable read order.
2. Canonical docs use deterministic names (no dates in filename).
3. Evidence docs keep dates in ISO format (`YYYY-MM-DD-*`).
4. Legacy docs preserve original names.
5. Each doc must include:
   - `Status`
   - `Class` (`canonical` / `reference` / `evidence` / `legacy`)
   - `Last updated`
   - `Owner`
   - `Depends on`
   - `Replaces` (if migrated)

## 7) Layer-by-Layer Migration Sequence

### Layer A: Skeleton

1. Create the new top-level folders and empty README indexes.
2. Add governance docs first (`GLOSSARY`, `CONSTANTS_AND_SEMANTICS`, standards).

### Layer B: Canonical Promotion

1. Promote highest-confidence documents into canonical spine.
2. Add `Replaces` pointers from old docs to new canonical paths.

### Layer C: Reference Consolidation

1. Move non-normative deep dives into `reference` sections.
2. Add concise summaries that link back to canonical docs.

### Layer D: Evidence and Legacy Freeze

1. Move dated records/assets under `07-evidence/`.
2. Move prototypes and superseded docs under `08-legacy/`.
3. Freeze legacy content as read-only historical context.

## 8) Immediate Next Moves

1. Approve this layout as the target structure.
2. Create folder skeleton + index READMEs without moving content yet.
3. Define first canonical set:
   - protocol
   - constants/semantics
   - architecture modes
   - risk/breakeven math
4. Start controlled migration with explicit source-to-target mapping in each moved file.
