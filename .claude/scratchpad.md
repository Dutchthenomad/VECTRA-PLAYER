# VECTRA-PLAYER Session Scratchpad

Last Updated: 2025-12-21 (Phase 12D Complete)

---

## Quick Start for Fresh Sessions

```bash
# Read key context files
Read the following files:
1. /home/nomad/Desktop/VECTRA-PLAYER/CLAUDE.md
2. /home/nomad/Desktop/VECTRA-PLAYER/.claude/scratchpad.md

# Run tests (VECTRA-PLAYER has its own venv now)
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short

# Check GitHub issues
gh issue list --repo Dutchthenomad/VECTRA-PLAYER
```

---

## Active Work

### Current Phase: Phase 12D - System Validation (COMPLETE)

**Branch:** `feat/phase-3-recording-consolidation`

**Latest Commit:** `89239b1` - `docs(Phase 12D): Add migration guide and update CLAUDE.md`

### Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 12A | Event Schemas | ✅ COMPLETE (58 tests) |
| 12B | Parquet Writer + EventStore | ✅ COMPLETE (84 tests) |
| 12C | LiveStateProvider | ✅ COMPLETE (20 tests) |
| 12D | System Validation & Legacy Consolidation | ✅ COMPLETE (8 tasks) |
| 12E | Protocol Explorer UI | ⏳ PENDING |

---

## Phase 12D Deliverables (Dec 21, 2025)

### UI Features
- **Capture Stats Panel** - Session ID (truncated), event count, periodic updates
- **Live Balance Display** - Server-authoritative cash from LiveStateProvider
- **LIVE Indicator** - Shows "LIVE: {username}" when CDP connected

### CLI Scripts
- `src/scripts/query_session.py` - DuckDB query tool (--stats, --recent N, --session ID)
- `src/scripts/export_jsonl.py` - Backwards-compatible JSONL export

### Infrastructure
- **TRADE_CONFIRMED Event** - Captures latency_ms for trade timing analysis
- **Legacy Deprecation Flags** - 6 env vars to control each legacy recorder
- **Migration Guide** - `docs/MIGRATION_GUIDE.md`

### Legacy Deprecation Flags
```bash
export LEGACY_RECORDER_SINK=false       # RecorderSink
export LEGACY_DEMO_RECORDER=false       # DemoRecorderSink
export LEGACY_RAW_CAPTURE=false         # RawCaptureRecorder
export LEGACY_UNIFIED_RECORDER=false    # UnifiedRecorder
export LEGACY_GAME_STATE_RECORDER=false # GameStateRecorder
export LEGACY_PLAYER_SESSION_RECORDER=false # PlayerSessionRecorder
```
Default: All `true` (backwards compatible)

---

## Test Coverage

```bash
# Run all tests
cd /home/nomad/Desktop/VECTRA-PLAYER/src
../.venv/bin/python -m pytest tests/ -v --tb=short

# Current: 1127 tests passing
```

---

## Data Directories

```
~/rugs_data/                          # RUGS_DATA_DIR (env var)
├── events_parquet/                   # Canonical truth store
│   ├── doc_type=ws_event/
│   ├── doc_type=game_tick/
│   ├── doc_type=player_action/
│   ├── doc_type=server_state/
│   └── doc_type=system_event/
├── exports/                          # JSONL exports (optional)
└── manifests/
```

---

## Key Documentation

| Document | Location |
|----------|----------|
| Migration Guide | `docs/MIGRATION_GUIDE.md` |
| Phase 12D Plan | `docs/plans/2025-12-21-phase-12d-system-validation-and-legacy-consolidation.md` |
| Phase 12 Design | `sandbox/2025-12-15-phase-12-unified-data-architecture-design.md` |

---

## Next Phase: 12E - Protocol Explorer UI

**Goals:**
1. Vector indexing with ChromaDB (reuse claude-flow infrastructure)
2. Protocol Explorer UI panel for querying captured events
3. Integration with rugs-expert agent

**Prerequisites:**
- Phase 12D complete ✅
- ChromaDB MCP server configured ✅

---

## GitHub Repository

**URL:** https://github.com/Dutchthenomad/VECTRA-PLAYER
**Branch:** `feat/phase-3-recording-consolidation`
**Status:** Up to date with origin

---

## Session History

- **2025-12-21**: Phase 12D complete - All 8 tasks, 1127 tests passing
- **2025-12-21**: Phase 12C complete - LiveStateProvider implemented
- **2025-12-17**: EventStore/Parquet writer development
- **2025-12-16**: Phase 12A complete (58 tests), pushed to GitHub
- **2025-12-15**: VECTRA-PLAYER forked from REPLAYER

---

## Related Projects

| Project | Location | Purpose |
|---------|----------|---------|
| REPLAYER | `/home/nomad/Desktop/REPLAYER/` | Production system |
| rugs-rl-bot | `/home/nomad/Desktop/rugs-rl-bot/` | RL training |
| claude-flow | `/home/nomad/Desktop/claude-flow/` | DevOps layer |
| Recordings | `/home/nomad/rugs_recordings/` | 929 games |
