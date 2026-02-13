# Probability

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `SURVIVAL_MODEL.md`, `BAYESIAN_RUG_SIGNAL.md`, `../../02-domain/DATA_MODEL/FEATURE_DICTIONARY.md`
Replaces: fragmented probability docs

## Purpose

Define canonical probability models used to estimate rug timing and edge.

## Scope

1. Survival-based baseline probability.
2. Bayesian signal updates and runtime scoring.
3. Probability output contract for downstream risk/strategy modules.

## Canonical Decisions

1. Survival model provides baseline conditional probability.
2. Bayesian signal layer adjusts baseline with feature/event evidence.
3. Probability outputs must expose confidence/quality metadata where possible.
