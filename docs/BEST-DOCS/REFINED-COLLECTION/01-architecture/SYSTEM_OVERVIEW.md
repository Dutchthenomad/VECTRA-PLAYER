# System Overview

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `SERVICE_BOUNDARIES.md`, `EVENT_MODEL.md`, `MODES_AND_EXECUTION_MODEL.md`
Replaces: mixed architecture overviews in source corpus

## Purpose

Provide a single, implementation-neutral architecture baseline for the next iteration.

## Scope

This document defines:

1. high-level topology,
2. component classes,
3. architectural principles,
4. non-goals for this section.

## Source Inputs

1. `system-extracts/README.md`
2. `system-extracts/01-minimal-trading-ui-foundation.md`
3. `system-extracts/02-explorer-ui-and-api.md`
4. `system-extracts/03-backtest-engine.md`
5. `system-extracts/06-live-simulator-paper-trading.md`
6. `system-extracts/08-containerization-and-plugin-patterns.md`
7. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
8. `PROCESS_FLOWCHARTS.md`

## Canonical Decisions

### 1) Target Topology

```text
Feed Adapters -> Foundation Core -> Event Stream -> Domain Services -> UI/BFF
                     |                 |                  |
                     v                 v                  v
               Command Gateway     Event Store       Ops/Monitoring
```

### 2) Component Classes

1. `adapter`: provider/environment-specific integrations (feed, browser, execution, storage).
2. `core`: provider-agnostic domain logic (normalization, strategy, simulation).
3. `service`: API/stream wrappers around core capabilities.
4. `artifact`: operator-facing UI modules (trade console, explorer).

### 3) Architectural Principles

1. Domain logic must not depend on Flask/SocketIO/browser tooling.
2. External integrations are injected via adapter boundaries.
3. APIs and events are versioned and schema-governed.
4. Every service exposes `GET /health` and `GET /ready`.
5. Heavy compute flows use async job patterns when runtime exceeds request budget.

### 4) Runtime Separation

1. `live-simulator` and `live-execution` are separate services.
2. Backtest/replay functionality is deterministic and data-versioned.
3. UI artifacts never call provider endpoints directly.

### 5) Storage and Truth Model

1. Event store (Parquet or equivalent) is canonical event history.
2. Derived indexes and views are rebuildable outputs, not primary truth.
3. All responses carrying computed outputs include source dataset/version metadata.

### 6) Non-Goals

1. This section does not lock implementation language/framework.
2. This section does not define strategy internals (handled in Section 3).
3. This section does not finalize deployment topology details (Section 5).

## Open Questions

1. Do we want a dedicated BFF service per UI (`trade-console-bff`, `explorer-bff`) or a unified gateway?
2. Should event retention policy be architecture-level or operations-level ownership?
