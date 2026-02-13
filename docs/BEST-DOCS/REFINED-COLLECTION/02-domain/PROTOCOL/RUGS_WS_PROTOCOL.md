# Rugs WebSocket Protocol

Status: in_review (Section 3)
Class: canonical
Last updated: 2026-02-12
Owner: Domain Review
Depends on: `REFERENCE_DATA_GUIDE.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: `rosetta-stone/ROSETTA-STONE.md` (as unified refined protocol target)

## Purpose

Provide canonical protocol semantics for ingestion and normalization layers.

## Scope

1. Raw feed lifecycle phases.
2. Core event families and minimum field set.
3. Normalization mapping hooks to architecture event schemas.

## Source Inputs

1. `rosetta-stone/ROSETTA-STONE.md`
2. `rosetta-stone/reference-data/game-20260206-003482fbeaae4ad5-full.json`
3. `rosetta-stone/reference-data/key-samples.json`
4. `Statistical Opt/07-FOUNDATION-SERVICE.md`

## Canonical Decisions

### 1) Lifecycle Phase Model

`cooldown -> presale -> active -> rugged`

Phase determination priority:

1. `active` and `rugged` booleans are authoritative.
2. `allowPreRoundBuys` governs presale eligibility.
3. Timer values are support signals, not sole phase authority.

### 2) Core Public Events (v1 baseline)

1. `gameStateUpdate`
2. `standard/newTrade`

Authenticated/private events are modeled as future extensions.

### 3) Minimum Canonical Raw Fields

For round/game state continuity:

- `gameId`
- `tickCount`
- `price`
- `active`
- `rugged`
- `cooldownTimer`
- `allowPreRoundBuys`

### 4) Protocol Timing Baseline

1. Nominal tick interval: `GAME_TICK_INTERVAL_NOMINAL_MS`.
2. Sidebet window baseline: `SIDEBET_WINDOW_TICKS`.
3. Cooldown/presale baseline constants follow governance constants table.

### 5) Protocol-to-Normalized Mapping Baseline

1. `gameStateUpdate` -> `market.tick`/phase events.
2. `standard/newTrade` -> `player.trade`.
3. Additional mapped events are extension-set, not v1 required baseline.

## Open Questions

1. Which authenticated events are required before protocol v1.1 can be marked complete?
2. Should transport framing details (Socket.IO envelope details) be first-class canonical content or appendix-only?
