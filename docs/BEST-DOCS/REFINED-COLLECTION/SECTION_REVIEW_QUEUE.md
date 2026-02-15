# Section Review Queue

Status: active
Last updated: 2026-02-12

## How We Review

1. Review one section at a time in order.
2. For the active section, reconcile source docs against stubs.
3. Capture decisions in canonical docs and decision log.
4. Mark section complete only after open questions are resolved.

## Ordered Queue

| Order | Section | Main Stub Path | Source Intake | Exit Criteria | Status |
|---|---|---|---|---|---|
| 1 | Governance | `00-governance/` | Root semantics and standards docs | Glossary, constants, and standards agreed | complete |
| 2 | Architecture | `01-architecture/` | `system-extracts/`, `Statistical Opt/00-07`, `PROCESS_FLOWCHARTS.md` | Unified architecture model + contracts baseline | in_review |
| 3 | Domain | `02-domain/` | `rosetta-stone/`, protocol notes in Statistical Opt | Protocol and domain rules normalized | in_review |
| 4 | Strategy and Math | `03-strategy-and-math/` | `risk_management/`, `PROBABILISTIC_REASONING.md`, statistical optimization docs, ML design docs | Canonical probability/risk/optimization/RL specs set | in_review |
| 5 | Systems | `04-systems/` | `system-extracts/`, `Statistical Opt/BACKTEST-TAB`, `Statistical Opt/EXPLORER-TAB`, code-examples | Per-system module docs aligned to architecture | in_review |
| 6 | Operations | `05-operations/` | `CHROME_PROFILE_SETUP.md`, runbooks in Scalp records and source docs | Run/deploy/test/monitor playbooks consolidated | in_review |
| 7 | Research | `06-research/` | `Scalp Research/HANDBOOK`, `PRNG CRACKING RESEARCH`, exploratory docs | Research canon separated from implementation canon | in_review |
| 8 | Evidence | `07-evidence/` | `Scalp Research/RECORDS`, checkpoints, figures, datasets | Evidence indexed with provenance and links | in_review |
| 9 | Legacy | `08-legacy/` | `Scalp Research/RECORDS/legacy-flat`, `bayesian prediction engine/` | Legacy archive boundaries finalized | in_review |

## Active Next Section

`Review Wave: Sections 2-9`

Working files:

1. `01-architecture/*`
2. `02-domain/*`
3. `03-strategy-and-math/*`
4. `04-systems/*`
5. `05-operations/*`
6. `06-research/*`
7. `07-evidence/*`
8. `08-legacy/*`
