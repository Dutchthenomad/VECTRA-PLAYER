# VECTRA-PLAYER Session Scratchpad

Last Updated: 2025-12-28 (Post MinimalWindow Session)

---

## CURRENT STATUS: Pipeline D Ready

**MinimalWindow:** ✅ COMPLETE (wiring fixes applied, tested, pushed)
**Pipeline A-C:** ✅ COMPLETE (all gates passed)
**Pipeline D:** ⏳ READY TO START

---

## What Was Accomplished (Dec 28, 2025)

### Session 1: MinimalWindow Implementation
- Replaced 8-mixin MainWindow (8,700 LOC) with MinimalWindow (850 LOC)
- 93% UI code reduction
- Archived 30 legacy UI files to `src/ui/_archived/`

### Session 2: Wiring Fixes
Fixed 4 blocking issues from audit:
- C1: `browser_bridge` passed to MinimalWindow
- H2: `LiveStateProvider` created in main.py
- H3: `EventStoreService` started in main.py
- H5: `BrowserBridge.on_status_change` callback wired

### Session 3: Documentation Cleanup
- Moved stale docs to `sandbox/DEVELOPMENT DEPRECATIONS/`
- Updated GLOBAL-DEVELOPMENT-PLAN.md with current status
- Consolidated development roadmap

---

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | App entry - all dependencies wired |
| `src/ui/minimal_window.py` | Minimal UI for RL training (850 LOC) |
| `docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` | Master plan (CANONICAL) |
| `docs/plans/2025-12-28-pipeline-d-training-data-implementation.md` | Pipeline D spec |
| `scripts/FLOW-CHARTS/observation-space-design.md` | 36-feature observation schema |

---

## Next Priority: Pipeline D

**Goal:** Generate RL training data from captured gameplay sessions

### Implementation Tasks (TDD Order)

1. **Create `src/ml/schemas.py`**
   - Observation dataclass with 36 features
   - FEATURE_NAMES list
   - to_numpy() method

2. **Create `src/ml/episode_segmenter.py`**
   - Segment events by game_id
   - Detect terminal states (rugged=True)
   - Filter short episodes

3. **Create `src/ml/observation_builder.py`**
   - Build 36-feature vectors from ws_events
   - Update from gameStateUpdate, playerUpdate
   - Compute derived features (velocity, acceleration)

4. **Create `src/ml/training_generator.py`**
   - Align observations with ButtonEvent actions
   - Create (obs, action, reward, next_obs, done) tuples
   - Generate batches for training

5. **Integration Test**
   - End-to-end with real Parquet data
   - Verify no NaN values
   - Validate tensor shapes

### Data Available

```
~/rugs_data/events_parquet/
├── doc_type=ws_event/      31,744 events
├── doc_type=button_event/     204 events
└── Distinct games:             59
```

### Gate Criteria

- [ ] Can generate valid training batches from recorded data
- [ ] 36-feature observations with correct shapes
- [ ] Episode boundaries correctly detected
- [ ] No NaN values in output tensors

---

## Commands

```bash
# Run app
cd /home/nomad/Desktop/VECTRA-PLAYER && ./run.sh

# Run tests (1138 passing)
cd src && ../.venv/bin/python -m pytest tests/ -v --tb=short

# Query Parquet
.venv/bin/python -c "import duckdb; print(duckdb.query('SELECT doc_type, COUNT(*) FROM read_parquet(\"/home/nomad/rugs_data/events_parquet/**/*.parquet\") GROUP BY doc_type').fetchall())"
```

---

## Related Repos

| Repo | Location | Purpose |
|------|----------|---------|
| rugs-rl-bot | `/home/nomad/Desktop/rugs-rl-bot/` | RL training, ML models |
| claude-flow | `/home/nomad/Desktop/claude-flow/` | Dev tooling, RAG knowledge |
| REPLAYER | `/home/nomad/Desktop/REPLAYER/` | Legacy (superseded by VECTRA) |

---

## Commits (Dec 28)

```
350f7d4 feat(ui): Add CONNECT button to MinimalWindow
52972c8 refactor(ui): Archive 30 deprecated UI files
26a1a2b feat(main): Replace MainWindow with MinimalWindow
3d6488a feat(ui): Wire WebSocket event handlers
22644e8 feat: Wire TradingController to MinimalWindow
6aecc4f feat(ui): Add MinimalWindow for RL training
91edbe6 docs: Add minimal UI design
340798a fix(ui): Wire MinimalWindow dependencies for functional CDP connection
```

---

*This scratchpad updated after MinimalWindow completion - December 28, 2025*
