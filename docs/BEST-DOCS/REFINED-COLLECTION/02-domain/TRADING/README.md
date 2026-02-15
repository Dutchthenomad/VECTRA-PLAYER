# Trading

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `MARKET_MECHANICS.md`, `POSITION_AND_SIDEBET_RULES.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: mixed trading-rule descriptions across strategy/risk docs

## Purpose

Define domain-level market and trading rules independent of strategy policy.

## Scope

1. Market lifecycle mechanics.
2. Position and sidebet rule semantics.
3. Rule boundaries vs strategy behavior.

## Canonical Decisions

1. Domain trading rules are policy-agnostic.
2. Strategy thresholds and edge assumptions are not encoded as market rules.
3. Payout semantics always use explicit `R_total`/`R_profit` notation.
