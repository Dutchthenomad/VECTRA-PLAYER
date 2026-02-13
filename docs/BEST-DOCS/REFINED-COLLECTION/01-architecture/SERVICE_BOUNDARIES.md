# Service Boundaries

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `SYSTEM_OVERVIEW.md`, `CONTRACTS/FOUNDATION_API.md`, `CONTRACTS/EVENT_SCHEMAS.md`
Replaces: implicit boundaries across source docs

## Purpose

Define clear ownership boundaries for services and artifacts in the target architecture.

## Scope

This section defines responsibilities and exclusions for the core service set.

## Source Inputs

1. `system-extracts/README.md`
2. `system-extracts/01-minimal-trading-ui-foundation.md`
3. `system-extracts/02-explorer-ui-and-api.md`
4. `system-extracts/03-backtest-engine.md`
5. `system-extracts/06-live-simulator-paper-trading.md`
6. `system-extracts/08-containerization-and-plugin-patterns.md`
7. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
8. `Statistical Opt/07-FOUNDATION-SERVICE.md`

## Canonical Decisions

### 1) Foundation Core Service

Owns:

1. feed normalization into canonical event types,
2. event stream publication,
3. command intake/routing baseline,
4. service health/readiness.

Does not own:

1. strategy computation,
2. Monte Carlo/backtest execution,
3. direct UI rendering.

### 2) Trade Console Artifact + Gateway

Owns:

1. operator intent capture and state rendering,
2. command submission through gateway APIs.

Does not own:

1. provider-specific execution code,
2. strategy autonomy logic.

### 3) Explorer Service/BFF

Owns:

1. analytics query orchestration,
2. result shaping for explorer UI,
3. async job status for heavy analysis.

Does not own:

1. raw data capture,
2. live trade execution.

### 4) Backtest Service

Owns:

1. deterministic session simulation over historical datasets,
2. tick/control APIs for reproducible replay-style strategy evaluation.

Does not own:

1. live feed subscriptions,
2. real-money execution.

### 5) Live Simulator Service

Owns:

1. paper-trading simulation on live normalized feed,
2. session state and simulated wallet lifecycle.

Does not own:

1. real-money order execution,
2. provider-specific transport normalization (adapter concern).

### 6) Execution Bridge Service

Owns:

1. real-order translation to provider execution endpoints,
2. execution acknowledgments and failure reporting.

Does not own:

1. simulation,
2. strategy policy logic.

### 7) Risk/Optimization Services

Owns:

1. position sizing, Monte Carlo, survival/Bayesian scoring, risk metrics.

Does not own:

1. UI concerns,
2. provider connectivity.

### 8) Data and State Ownership

1. Event history is produced by ingestion/foundation pipelines.
2. Session state is externalized (not in-process singleton) for service resiliency.
3. Every service response that depends on data must include dataset/version identifiers.

### 9) Boundary Enforcement Rules

1. No hardcoded host/port/path in domain logic.
2. No direct feed/vendor coupling inside strategy/risk modules.
3. No framework-specific imports in pure domain packages.
4. Service-to-service coupling only via versioned APIs/events.

## Open Questions

1. Should `execution-bridge-service` be mandatory in all deployments, or optional plugin profile?
2. Should backtest and live-simulator share one domain engine package with two adapters, or stay fully separate?
