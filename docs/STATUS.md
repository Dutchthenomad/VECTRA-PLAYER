# VECTRA-PLAYER Project Status

**Last Updated:** 2026-01-17
**Status:** Active Development
**Schema Version:** 2.0.0

---

## Canonical Status Sources

- **This file** is the source of truth for current status.
- **`docs/plans/GLOBAL-DEVELOPMENT-PLAN.md`** is the active roadmap.
- **`docs/ARCHITECTURE.md`** documents system architecture.
- Superseded documents are archived in `sandbox/DEVELOPMENT DEPRECATIONS/`.

---

## Current State Summary

VECTRA-PLAYER is a unified data architecture for rugs.fun, providing:
- Real-time WebSocket data capture via Chrome DevTools Protocol
- Event normalization and persistence to Parquet
- Browser-based recording UI and trading controls
- Foundation Service for HTML artifact development (on feature branch)

---

## Branch Status

| Branch | Purpose | Status |
|--------|---------|--------|
| `main` | Production-ready code | Current |
| `feature/typescript-frontend-api` | Foundation Service + API redesign | **Ready to merge** |
| `auto-claude/001-*` | Development environment automation | Active |
| `auto-claude/002-*` | Pipeline D training data | Active |

---

## Component Status

### Core Infrastructure (main branch)

| Component | Status | Location |
|-----------|--------|----------|
| EventBus | Production | `src/services/event_bus.py` |
| EventStore | Production | `src/services/event_store/` |
| LiveStateProvider | Production | `src/services/live_state_provider.py` |
| BrowserBridge (CDP) | Production | `src/services/browser_bridge.py` |
| BotActionInterface | Complete | `src/bot_action/` |

### Recording UI (main branch)

| Component | Status | Port |
|-----------|--------|------|
| Flask App | Production | 5000 |
| Browser Service | Production | - |
| Dashboard Templates | Production | - |
| Static JS/CSS | Production | - |

### Foundation Service (feature branch - READY TO MERGE)

| Component | Status | Port |
|-----------|--------|------|
| WebSocket Broadcaster | Complete | 9000 |
| HTTP Monitor | Complete | 9001 |
| Event Normalizer | Complete | - |
| Launcher | Complete | - |

### PRNG Analysis Tools (main branch)

| Component | Status | Location |
|-----------|--------|----------|
| Games Dataset | Complete | `src/rugs_recordings/PRNG CRAK/games_dataset.jsonl` (2,835 games) |
| Explorer v2 | Complete | `src/rugs_recordings/PRNG CRAK/explorer_v2/` |
| Prediction Engine | Complete | `src/rugs_recordings/PRNG CRAK/prediction_engine/` |
| Parameter Optimizer | Complete | `src/rugs_recordings/PRNG CRAK/parameter_optimizer/` |

---

## Phase Status Overview

### Completed Phases

| Phase | Description | Completion Date |
|-------|-------------|-----------------|
| 12A | Event schemas (58 tests) | 2025-12 |
| 12B | Parquet Writer + EventStore (84 tests) | 2025-12 |
| 12C | LiveStateProvider (20 tests) | 2025-12 |
| 12D | System validation & legacy consolidation | 2025-12 |
| Schema v2.0.0 | Expanded event schema design | 2025-12-23 |
| MinimalWindow | UI simplification (93% code reduction) | 2025-12-28 |
| Pipeline A | Server state validation | 2025-12-27 |
| Pipeline B | ButtonEvent implementation | 2025-12-27 |
| Pipeline C | Player action validation | 2025-12-28 |
| Phase 6 | BotActionInterface (166 tests) | 2025-12-25 |
| Migration | Environment stabilization | 2026-01-03 |

### In Progress (Current Priority)

| Phase | Description | Status |
|-------|-------------|--------|
| **Foundation Merge** | WebSocket broadcaster | Ready to merge |
| **Consolidation** | Documentation update | In progress |
| Pipeline D | Training data pipeline | Ready to start |
| HTML Artifacts | Prediction engine, seed bruteforce | Planning |

### Pending

| Phase | Description | Blocker |
|-------|-------------|---------|
| 12E | Protocol Explorer UI | Pipeline D |
| Audit 6 | Gated development validation | Pipeline D |
| Audit 7 | UI redesign prep | Audit 6 |

---

## Test Status

```
Total Tests: 1149+ passing
Last Run: 2025-12-28

Test Command:
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short
```

---

## Data Inventory

### Parquet Store (`~/rugs_data/events_parquet/`)

| DocType | Event Count | Description |
|---------|-------------|-------------|
| ws_event | ~31,744 | Raw WebSocket events |
| button_event | ~204 | Human trading actions |
| game_tick | Growing | Price/tick stream |
| server_state | Growing | Player balance/position |

### Games Dataset

- **Location:** `src/rugs_recordings/PRNG CRAK/games_dataset.jsonl`
- **Games:** 2,835
- **Fields:** game_id, seed, final_price, duration_ticks, peak_multiplier, etc.

---

## Port Configuration

| Service | Port | Status |
|---------|------|--------|
| Flask Recording UI | 5000 | Production |
| Foundation WebSocket | 9000 | Ready (feature branch) |
| Foundation Monitor | 9001 | Ready (feature branch) |
| Chrome CDP | 9222 | Production |

---

## Critical Decision: Shorting Deferred (2025-12-24)

rugs-expert agent confirmed **no empirical data exists** for shorting:
- `shortPosition` always `null` in all WebSocket captures
- No `shortOrder` events documented
- UI buttons and mechanics unknown

**Action:** Shorting removed from v1.0 scope. Research continues in claude-flow.

---

## Key Reference Documents

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Project instructions for Claude |
| `docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` | Master development roadmap |
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/plans/2026-01-17-consolidation-plan.md` | Current implementation plan |
| `docs/specs/WEBSOCKET_EVENTS_SPEC.md` | WebSocket protocol spec |
| `src/rugs_recordings/PRNG CRAK/HAIKU-CRITICAL-FINDINGS.md` | Prediction algorithms |

---

## Next Actions (Priority Order)

1. **Merge Foundation Service branch to main**
2. **Update CLAUDE.md with Foundation Service documentation**
3. **Build HTML artifact framework**
   - foundation-ws-client.js
   - Seed bruteforce tool
   - Prediction engine
   - Orchestrator wrapper

---

## Recent Accomplishments

| Date | Event | Description |
|------|-------|-------------|
| 2026-01-17 | Consolidation | STATUS.md, ARCHITECTURE.md updated |
| 2026-01-15 | Design | TypeScript Frontend API plan created |
| 2026-01-03 | Priority 1 | Migration stabilization complete |
| 2026-01-02 | Config | Chrome `rugs_bot` profile configured as default |
| 2025-12-28 | Milestone | MinimalWindow implementation complete |
| 2025-12-26 | Issues | #138-140 closed (toast, paths, legacy cleanup) |
| 2025-12-25 | Phase 6 | BotActionInterface COMPLETE - 166 tests |
| 2025-12-24 | Decision | Shorting deferred - no empirical data |

---

## Archive Policy

If a status, audit, plan, or summary doc is replaced by this file or
`docs/ROADMAP.md`, it should be moved to
`sandbox/DEVELOPMENT DEPRECATIONS/` rather than deleted.

---

*Last updated: 2026-01-17*
