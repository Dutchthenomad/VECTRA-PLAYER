# Event Schemas

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `../EVENT_MODEL.md`, `../../00-governance/GLOSSARY.md`
Replaces: ad hoc event payloads and wrapper variants in source docs

## Purpose

Define baseline event schemas used across stream and internal bus contracts.

## Scope

Schema definitions for envelope and high-value event types.

## Source Inputs

1. `Statistical Opt/03-EVENT-SYSTEM.md`
2. `Statistical Opt/07-FOUNDATION-SERVICE.md`
3. `system-extracts/01-minimal-trading-ui-foundation.md`
4. `system-extracts/06-live-simulator-paper-trading.md`
5. `PROCESS_FLOWCHARTS.md`
6. `rosetta-stone/ROSETTA-STONE.md`

## Canonical Decisions

### 1) Canonical Event Envelope (v1)

```json
{
  "version": "v1",
  "id": "uuid",
  "type": "market.tick",
  "ts": 1737830112000,
  "source": "foundation-core",
  "correlation_id": null,
  "game_id": "20260206-003482fbeaae4ad5",
  "data": {}
}
```

Field requirements:

1. required: `version`, `id`, `type`, `ts`, `source`, `data`
2. optional: `correlation_id`, `game_id`

### 2) `market.tick` Schema (v1)

```json
{
  "type": "market.tick",
  "data": {
    "tick": 103,
    "price": 1.2842,
    "active": true,
    "rugged": false,
    "phase": "active"
  }
}
```

### 3) `player.state` Schema (v1)

```json
{
  "type": "player.state",
  "data": {
    "cash": 12.34,
    "position_qty": 1.0,
    "avg_cost": 1.22,
    "pnl": 0.18
  }
}
```

### 4) `player.trade` Schema (v1)

```json
{
  "type": "player.trade",
  "data": {
    "side": "buy|sell|short_open|short_close",
    "qty": 1.0,
    "price": 1.45,
    "username": "optional"
  }
}
```

### 5) `sidebet.placed` and `sidebet.result`

`sidebet.placed`:

```json
{
  "type": "sidebet.placed",
  "data": {
    "start_tick": 200,
    "window_ticks": 40,
    "amount": 0.01,
    "r_total": 5,
    "r_profit": 4
  }
}
```

`sidebet.result`:

```json
{
  "type": "sidebet.result",
  "data": {
    "won": true,
    "payout_amount": 0.05,
    "settlement_tick": 235
  }
}
```

### 6) Session Events

`session.tick`:

```json
{
  "type": "session.tick",
  "data": {
    "session_id": "uuid",
    "mode": "backtest|live-simulator",
    "wallet": {},
    "stats": {}
  }
}
```

`session.state_changed`:

```json
{
  "type": "session.state_changed",
  "data": {
    "session_id": "uuid",
    "from": "running",
    "to": "paused"
  }
}
```

### 7) Command Events

`command.accepted` and `command.failed` must carry `correlation_id` pointing to original command.

### 8) Schema Discipline

1. Do not wrap envelopes inside envelopes.
2. Event `type` values are lowercase dotted namespaces.
3. Additive fields are allowed in minor revisions; breaking changes require new version.

## Open Questions

1. Should we split stream schemas by channel (public vs operator/authenticated), or rely on one schema with optional fields?
2. Do we standardize numeric precision/decimal encoding at schema level in this section or defer to domain section?
