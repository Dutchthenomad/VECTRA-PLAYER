# Optimization

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `MONTE_CARLO.md`, `STRATEGY_PROFILE_GENERATION.md`
Replaces: optimization docs spread across source corpus

## Purpose

Define canonical optimization workflows and output contracts.

## Scope

1. Monte Carlo simulation and comparison.
2. Strategy profile generation and ranking.
3. Reproducibility and metadata requirements.

## Canonical Decisions

1. Long-running optimization jobs should be async and reproducible.
2. Every optimization run must capture config, data version, and seed.
3. Output profiles are artifacts feeding systems and operations decisions.
