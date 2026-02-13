# Architecture

Status: in_review (Section 2)
Class: canonical
Last updated: 2026-02-12
Owner: Architecture Review
Depends on: `../00-governance/GLOSSARY.md`, `../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: architecture guidance spread across source corpus

## Purpose

Define the canonical architecture model and service boundaries for the next-iteration system.

## Scope

This section covers:

1. System topology and component responsibilities.
2. Service boundaries and ownership lines.
3. Event envelope and event taxonomy.
4. Runtime modes and allowed execution semantics.
5. Foundation HTTP and stream contract baseline.

## Contents

1. `SYSTEM_OVERVIEW.md`
2. `SERVICE_BOUNDARIES.md`
3. `EVENT_MODEL.md`
4. `MODES_AND_EXECUTION_MODEL.md`
5. `CONTRACTS/FOUNDATION_API.md`
6. `CONTRACTS/EVENT_SCHEMAS.md`

## Primary Source Inputs

1. `system-extracts/README.md`
2. `system-extracts/01-minimal-trading-ui-foundation.md`
3. `system-extracts/02-explorer-ui-and-api.md`
4. `system-extracts/03-backtest-engine.md`
5. `system-extracts/06-live-simulator-paper-trading.md`
6. `system-extracts/08-containerization-and-plugin-patterns.md`
7. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
8. `Statistical Opt/03-EVENT-SYSTEM.md`
9. `Statistical Opt/07-FOUNDATION-SERVICE.md`
10. `PROCESS_FLOWCHARTS.md`
