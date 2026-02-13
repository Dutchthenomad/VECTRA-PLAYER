# Market Mechanics

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `POSITION_AND_SIDEBET_RULES.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: lifecycle/mechanics sections in source docs

## Purpose

Capture game-market mechanics that are treated as environment rules.

## Scope

1. Round lifecycle semantics.
2. Time/tick mechanics.
3. Rug termination behavior.

## Source Inputs

1. `rosetta-stone/ROSETTA-STONE.md`
2. `PRNG CRACKING RESEARCH/PRNG-QUICK-REFERENCE.md`
3. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`

## Canonical Decisions

1. Market lifecycle follows `cooldown -> presale -> active -> rugged`.
2. Tick interval uses nominal timing constant; jitter is expected.
3. Rugged state terminates active round and triggers settlement/cooldown sequence.
4. Lifecycle flags (`active`, `rugged`, `allowPreRoundBuys`) outrank timer-only inference.

## Open Questions

1. Should separate mechanic profiles exist for environments with altered payout/rug parameters?
