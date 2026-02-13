# VECTRA System Extraction Bundle (Revised for Agnostic Rebuild)

Date: 2026-02-12
Audience: Lead Developer Review

This is the revised extraction set focused on portability.

## Revision Goals

- Make service boundaries environment-agnostic.
- Separate domain logic from UI, transport, and provider-specific integrations.
- Keep legacy source snippets as evidence, but define clean target contracts.

## Cross-Cutting Cleanup Rules

1. No hardcoded filesystem paths.
2. No hardcoded hostnames, ports, or provider URLs in domain logic.
3. No direct feed/vendor coupling inside strategy engines.
4. Domain modules must run without Flask/SocketIO/browser dependencies.
5. Heavy compute endpoints must support async jobs.
6. Every service must expose `GET /health` and `GET /ready`.
7. All external dependencies must be injected via config + adapters.
8. All APIs must publish versioned request/response schemas.

## Documents

1. `01-minimal-trading-ui-foundation.md`
2. `02-explorer-ui-and-api.md`
3. `03-backtest-engine.md`
4. `04-bankroll-position-sizing.md`
5. `05-monte-carlo-comparison.md`
6. `06-live-simulator-paper-trading.md`
7. `07-offline-v1-simulator-artifact.md`
8. `08-containerization-and-plugin-patterns.md`

## Source Repositories Used

- `/home/devops/Desktop/VECTRA-PLAYER`
- `/home/devops/Desktop/VECTRA-BOILERPLATE`

## Deliverable Intent

Each document now includes:

- Legacy extraction notes (what exists today)
- Agnostic target boundary (what to build next)
- Service contract recommendations (API/event/data)
- Cleanup checklist for migration
