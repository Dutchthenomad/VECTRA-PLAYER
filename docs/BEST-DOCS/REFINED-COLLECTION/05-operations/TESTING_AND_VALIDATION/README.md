# Testing and Validation

Status: in_review (Section 6)
Class: canonical
Last updated: 2026-02-12
Owner: Operations Review
Depends on: `../README.md`, `../../03-strategy-and-math/README.md`
Replaces: scattered test and validation notes

## Purpose

Define testing and validation standards for architecture, strategy, and operations confidence.

## Scope

1. contract tests,
2. simulation/backtest validation,
3. regression and reproducibility checks,
4. signoff criteria.

## Canonical Decisions

1. Contract tests are required for API and event schema stability.
2. Strategy changes require reproducible backtest/simulation evidence.
3. Validation outcomes must be logged into evidence section.
