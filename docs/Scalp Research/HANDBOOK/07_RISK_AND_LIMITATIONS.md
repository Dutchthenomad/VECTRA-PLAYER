# 07 Risk and Limitations

Status: active
Last validated: 2026-02-08

## Purpose

Capture known methodological and system risks that constrain interpretation of current results.

## Critical Risks

1. In-sample selection bias risk.
- If permutation/threshold selection and scoring are done on the same sample, performance can be inflated.

2. Bankroll path realism gap.
- Fixed-stake aggregate PnL can hide drawdown/ruin behavior if affordability and sequence constraints are not enforced.

## High Risks

1. Exit mischaracterization risk.
- Very wide TP/SL settings can make apparent TP/SL optimization mostly a time-exit effect.

2. Dataset quick-sample bias.
- Time-biased quick slices can overfit current regime composition.

3. Assumption drift.
- If scope assumptions and active experiments diverge, decisions can be made from stale constraints.

## Medium Risks

1. Static planning drift.
- Hardcoded planner assumptions can diverge from checkpoint reality.

2. Reproducibility friction.
- Without deterministic run manifests, exact replay can degrade over time.

3. Canonical/hypothesis mixing.
- Unlabeled speculative claims can contaminate decision surfaces and downstream RAG usage.

## Current Mitigation Policy

1. Treat `06_RESULTS_CANONICAL.md` as single source of current truth.
2. Keep dated outputs in `RECORDS/` and avoid back-editing conclusions into canonical docs without validation.
3. Require split-stability checks before promotion.
4. Keep short-side policies sandboxed until robust.

## Remaining Limitations

1. Fee/rake adjustments are not fully integrated across all evaluation paths.
2. Full walk-forward validation is pending.
3. Confidence intervals/uncertainty bands are not yet mandatory in all reports.
4. Live pipeline contract hardening is not complete (tracked in audits).

## Risk Acceptance for Current Stage

Current research outputs are acceptable for exploratory prioritization, not for production execution claims.

## Audit References

1. `../RECORDS/audits/2026-02-08-comprehensive-audit.md`
2. `../RECORDS/audits/2026-02-08-v2-pipeline-context-audit.md`
