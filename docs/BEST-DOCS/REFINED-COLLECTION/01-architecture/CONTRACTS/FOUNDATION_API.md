# Foundation API Contract

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `../EVENT_MODEL.md`, `../MODES_AND_EXECUTION_MODEL.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: mixed endpoint patterns in source docs

## Purpose

Define the baseline HTTP contract surface for foundation and related orchestration services.

## Scope

This is a canonical baseline contract, not a full implementation spec.

## Source Inputs

1. `system-extracts/README.md`
2. `system-extracts/01-minimal-trading-ui-foundation.md`
3. `system-extracts/02-explorer-ui-and-api.md`
4. `system-extracts/03-backtest-engine.md`
5. `system-extracts/06-live-simulator-paper-trading.md`
6. `system-extracts/08-containerization-and-plugin-patterns.md`
7. `Statistical Opt/07-FOUNDATION-SERVICE.md`

## Canonical Decisions

### 1) Base Response Envelope

All JSON responses:

```json
{
  "version": "v1",
  "status": "ok|error",
  "request_id": "uuid",
  "data": {}
}
```

### 2) Required Service Health Endpoints

1. `GET /health` -> process-level liveness.
2. `GET /ready` -> dependency/readiness status.
3. `GET /metrics` -> optional but strongly recommended.

### 3) Stream Endpoint

1. `GET /state/stream` (SSE or WS adapter surface).
2. Stream payloads must follow event envelope defined in `EVENT_SCHEMAS.md`.

### 4) Command Endpoint

1. `POST /commands/trade`
2. `POST /commands/percentage`
3. `POST /commands/bet-adjust`

Trade command payload baseline:

```json
{
  "command_id": "uuid",
  "action": "BUY|SELL|SIDEBET",
  "amount": 0.01,
  "metadata": {
    "ui_session": "string"
  }
}
```

### 5) Sessioned Backtest Contract

1. `POST /backtest/sessions`
2. `GET /backtest/sessions/{id}`
3. `POST /backtest/sessions/{id}/tick`
4. `POST /backtest/sessions/{id}/control`
5. `DELETE /backtest/sessions/{id}`

### 6) Sessioned Live Simulator Contract

1. `POST /live-sim/sessions`
2. `GET /live-sim/sessions/{id}`
3. `POST /live-sim/sessions/{id}/stop`
4. `GET /live-sim/sessions/{id}/stream`

### 7) Explorer Orchestration Contract

1. `GET /explorer/strategy`
2. `POST /explorer/bankroll/run`
3. `POST /explorer/monte-carlo/run`
4. `GET /explorer/jobs/{job_id}`

### 8) Payout Field Contract

When payout appears in API payloads:

1. `r_total` is required.
2. `r_profit` is optional but recommended.
3. if both are present, enforce `r_total = r_profit + 1`.

### 9) Error Shape

Error responses:

```json
{
  "version": "v1",
  "status": "error",
  "request_id": "uuid",
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### 10) Versioning Rule

All endpoint contracts and payload schemas are versioned. Breaking changes require version bump and migration notes.

## Open Questions

1. Should we adopt a single API namespace prefix (`/api/v1`) now, or defer to Section 5 operations/deployment decisions?
2. Should command endpoints be synchronous-ack only with async outcome events, or allow inline execution result for low-latency paths?
