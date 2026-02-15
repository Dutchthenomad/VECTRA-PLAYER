# Event Model

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `../00-governance/GLOSSARY.md`, `CONTRACTS/EVENT_SCHEMAS.md`
Replaces: fragmented event descriptions in source docs

## Purpose

Define the canonical event envelope, taxonomy, and delivery expectations.

## Scope

Applies to all internal and external events emitted by core and service layers.

## Source Inputs

1. `system-extracts/README.md`
2. `system-extracts/01-minimal-trading-ui-foundation.md`
3. `system-extracts/06-live-simulator-paper-trading.md`
4. `Statistical Opt/03-EVENT-SYSTEM.md`
5. `Statistical Opt/07-FOUNDATION-SERVICE.md`
6. `PROCESS_FLOWCHARTS.md`

## Canonical Decisions

### 1) Event Envelope

All events use:

```json
{
  "version": "v1",
  "id": "uuid",
  "type": "domain.topic",
  "ts": 1737830112000,
  "source": "service-name",
  "correlation_id": "uuid-or-null",
  "game_id": "optional-game-id",
  "data": {}
}
```

### 2) Event Type Namespaces

1. `market.*` for market/game feed state.
2. `player.*` for player state and trades.
3. `sidebet.*` for sidebet lifecycle.
4. `session.*` for backtest/live-simulator session state.
5. `command.*` for command acknowledgments/failures.
6. `system.*` for health/errors/lifecycle.

### 3) Canonical Market Lifecycle

1. `market.cooldown`
2. `market.presale`
3. `market.tick`
4. `market.rugged`

Lifecycle transitions must be monotonic within a game session.

### 4) Delivery Guarantees (Baseline)

1. At-most-once delivery is acceptable for UI stream consumption.
2. Persistent event store is the source of replay/recovery truth.
3. Consumers must tolerate missing non-critical interim ticks.
4. Order is preserved per source stream where transport allows.

### 5) Event Schema Governance

1. Event envelope version bumps are explicit (`v1`, `v2`).
2. Breaking payload changes require new event schema version.
3. Services must reject malformed events and emit `system.error`.

### 6) Unwrapping Rule

Legacy nested wrappers found in source code are non-canonical. Refined services emit only a single canonical envelope.

### 7) Correlation and Traceability

1. Commands and resulting events share `correlation_id`.
2. Async jobs include a stable `job_id` in `data`.
3. Derived events should retain source identifiers in metadata.

## Open Questions

1. Do we require exactly-once semantics for any subset of command outcomes?
2. Should `game_id` be mandatory for all `market.*` and `sidebet.*` events?
