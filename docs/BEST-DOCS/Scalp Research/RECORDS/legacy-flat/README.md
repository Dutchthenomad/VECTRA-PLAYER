# Scalp Trading Research Index

Last updated: 2026-02-08

This folder is the dedicated research checkpoint for scalping strategy exploration.
It is structured to preserve:

- Empirical facts (what the data has already shown)
- Foundational assumptions (what the simulator is and is not modeling)
- Theoretical avenues (high-value hypotheses still under test)
- Execution plans (Bayesian optimization + Monte Carlo robustness)

## Core Documents

1. `SCALPING-EMPIRICAL-FACTS.md`
- Dated, reproducible metric snapshot from canonical recorded games.
- Includes one-tick to ten-tick return envelopes, 5-tick MFE/MAE, touch rates, and first-touch behavior.

2. `SCALPING-FOUNDATIONS-ASSUMPTIONS.md`
- Scope boundaries, definitions, simulator mechanics, and modeling constraints.

3. `SCALPING-THEORETICAL-AVENUES.md`
- Hypothesis backlog prioritized by expected value for finding durable edge.

4. `SCALPING-BO-MONTE-CARLO-PLAN.md`
- Concrete execution protocol for entry-first optimization and robustness simulation.

5. `SCALPING-KICKOFF-RUN-MATRIX.md`
- First-cycle executable run matrix and default exploration settings.

6. `SCALPING-KICKOFF-RUN-RESULTS-2026-02-08.md`
- Executed Stage A/B + full-grid outcomes, recommended exploration ranges, and observed PnL envelope.

7. `SCALPING-V1-SIMULATOR-OBSERVATIONS-2026-02-08.md`
- Dated operational findings from the V1 toggleable bot simulator 500-game run (per-game SOL outcomes, regime/exits implications).

8. `SCALPING-V1-TOGGLE-TEST-MATRIX.md`
- Immediate controlled experiment matrix for V1 policy toggles before Monte Carlo promotion.

9. `SCALPING-V2-PIPELINE-CONTEXT-AUDIT-2026-02-08.md`
- Cross-audit of `rugs-data-pipeline` and `knowledge-export` against current scalping methodology.
- Captures verified integration gaps, contract mismatches, and V2 sequencing recommendations.

10. `SCALPING-CLASSIFICATION-AND-REGIME-PRIMER.md`
- Plain-language explanation of how classifier features, threshold ordering, regime labels, and playbook routing work.
- Includes exact regime gate map and practical implications of `AUTO_REGIME` vs fixed-playbook mode.

11. `SCALPING-TA-TOOLKIT-BRAINSTORM.md`
- Research blueprint for price-only TA conversions and mechanistic Bayesian regime modeling.
- Defines candidate feature families, posterior metrics, rug-over-hold math, and high-tier alpha hypotheses.

12. `SCALPING-LONG-SHORT-EDGE-STUDY-2026-02-08.md`
- Real-game tick study comparing long rebound and short fade/continuation windows.
- Documents concentrated long-edge zone, short-side instability findings, and V2 prioritization guidance.

13. `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md`
- Larger-pass validation on `min60` and expanded `min30` datasets using one-trade-per-game realism.
- Defines tested trigger variants and the tentatively validated higher-order method (`HOS_V1 Score-Routed`).

14. `SCALPING-SESSION-CLOSEOUT-2026-02-08.md`
- Consolidated checkpoint separating validated facts, open hypotheses, decisions made, and V2 next-step order.
- Primary "resume point" document for continuing the research without losing context.

15. `SCALPING-DOCS-REFACTOR-PLAN-2026-02-08.md`
- Full information-architecture refactor plan for converting the current flat research set into a canonical handbook + immutable records model.
- Includes severity-ranked doc findings, migration map for every current file, phased execution, and definition of done.

## Existing Operational Docs

1. `SCALPING-DATASET-COLLECTION-REPORT.md`
- Canonical source selection and dataset export results.

2. `SCALPING-EXPLORER-RUNBOOK.md`
- Reliable launch/serve procedure for the artifact.

3. `src/artifacts/tools/scalping-optimization-planner/index.html`
- Visual planning artifact for run-matrix sizing and kickoff markdown generation.

4. `figures/index.html`
- Visual outcome report (SVG charts) for envelope bounds, distribution, mode/drift comparison, and range concentration.

5. `src/artifacts/tools/scalping-bot-v1-simulator/index.html`
- Dedicated V1 toggleable bot simulator (preset-driven) with primary/secondary outcome windows and single-game trace inspection.

6. `SCALPING-V1-SIMULATOR-RUNBOOK.md`
- Reliable launch/serve and smoke checklist for the V1 simulator artifact.

## Current State Snapshot

As of `2026-02-08`, the research status is:

1. Canonical optimization sweep complete on `1,772` games with robust exploration ranges identified.
2. Larger-pass trigger validation completed on `min30` (`2,056` games); `HOS_V1 Score-Routed` is the current tentative default policy.
3. Visual reporting available in `figures/index.html` for envelope and concentration analysis.
4. V1 toggleable simulator implemented and running for policy prototyping on prerecorded games.
5. Latest 500-game V1 run indicates usable signal with visible downside asymmetry and exit-behavior improvements still needed.
6. Pipeline context audit completed against `rugs-data-pipeline` + `knowledge-export`; critical contract fixes identified before V2 live progression.
7. Session-wide closeout checkpoint created to lock facts vs hypotheses before V2 expansion.

## Reproducibility Artifacts

Path: `checkpoints/`

1. `checkpoints/scalping_empirical_checkpoint_2026-02-08.json`
- Empirical descriptive stats from canonical `min60` dataset.

2. `checkpoints/scalping_tp_sl_timeexit_checkpoint_2026-02-08.json`
- 5-tick TP/SL + fallback time-exit grid snapshot.

3. `checkpoints/scalping_opt_sweep_2026-02-08.json`
- Stage A/B shortlist sweep result used to derive robust exploration ranges.

4. `checkpoints/scalping_opt_fullgrid_envelope_2026-02-08.json`
- Full 2,100-config envelope for global net/end SOL bounds.

## Working Rule (to prevent loss)

- Add new dated checkpoint files instead of overwriting prior snapshots.
- Keep empirical and theoretical content separated.
- Update this index whenever a new research checkpoint is created.
