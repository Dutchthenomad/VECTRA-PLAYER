# VECTRA-PLAYER: Consolidation & Artifact Framework Plan

**Date:** 2026-01-17
**Status:** APPROVED - Implementation In Progress
**Purpose:** Consolidate project state, merge Foundation Service, clean up codebase, then build HTML artifact framework

---

## Priority Order

1. **Write this context to project docs** (prevent context loss)
2. **Merge Foundation Service to main** (prerequisite for all tools)
3. **Archive deprecated code & update documentation**
4. **Build HTML artifact framework** (prediction engine, seed bruteforce)

---

## Part A: Context Preservation (FIRST PRIORITY)

**Problem:** Critical context scattered across session, not persisted to project.

**Solution:** Write consolidated project state to canonical location.

### Files to Create/Update

| File | Content |
|------|---------|
| `docs/STATUS.md` | Current project state, what's complete, what's pending |
| `docs/ARCHITECTURE.md` | System architecture including Foundation Service |
| `CLAUDE.md` | Update with Foundation Service info, current priorities |
| `docs/plans/2026-01-17-consolidation-plan.md` | This plan (permanent record) |

### Key Context to Preserve

1. **Foundation Service** exists on `feature/typescript-frontend-api` branch
   - WebSocket broadcaster on port 9000
   - Monitoring UI on port 9001
   - Normalized event types (game.tick, player.state, etc.)

2. **PRNG CRAK findings** (in `src/rugs_recordings/PRNG CRAK/`)
   - Algorithm mismatch confirmed
   - Mean-reversion patterns detected
   - Prediction engine design in HAIKU-CRITICAL-FINDINGS.md

3. **Current architecture**
   - Flask-SocketIO on port 5000 (recording UI)
   - Foundation Service on port 9000/9001 (new, not merged)
   - EventBus + EventStore for data flow

---

## Part B: Merge Foundation Service (SECOND PRIORITY)

**Current State:** Foundation code exists in git but not on main branch.

```bash
# Check current branch
git branch -v

# Merge Foundation to main
git checkout main
git merge feature/typescript-frontend-api

# Verify merge
python -m foundation.launcher --help
```

### Foundation Service Files (from feature branch)

```
src/foundation/
├── __init__.py
├── config.py           # FoundationConfig with env vars
├── connection.py       # ConnectionState machine
├── normalizer.py       # Event normalization
├── broadcaster.py      # WebSocket server (port 9000)
├── service.py          # FoundationService orchestrator
├── http_server.py      # Monitoring UI (port 9001)
├── runner.py           # CLI runner
└── launcher.py         # Full startup with Chrome/CDP
```

---

## Part C: Codebase Cleanup (THIRD PRIORITY)

### Deprecated Code to Archive

| Location | Reason | Action |
|----------|--------|--------|
| `src/services/recording_state_machine.py` | Removed in 3599e1e | Already deleted |
| `src/ui/_archived/` | Old 8-mixin UI | Keep archived |
| Legacy recorders | Replaced by EventStore | Verify deleted |
| `sandbox/DEVELOPMENT DEPRECATIONS/` | Old phase docs | Keep as historical |

### Documentation Updates Needed

| File | Current State | Updates Needed |
|------|---------------|----------------|
| `CLAUDE.md` | References Flask on port 5000 | Add Foundation Service (9000/9001) |
| `docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` | Phase 12 focus | Add Phase 13 (Foundation) |
| `docs/MIGRATION_GUIDE.md` | Phase 12 focus | Add Foundation Service migration section |
| `README.md` (if exists) | Unknown | Verify current |

### Scripts to Audit

```bash
# Find potentially deprecated scripts
find scripts/ -name "*.py" -mtime +30  # Not modified in 30 days
find src/ -name "*deprecated*" -o -name "*legacy*"
```

---

## Part D: HTML Artifact Framework (FOURTH PRIORITY)

### Directory Structure

```
src/artifacts/                          # NEW: HTML Artifact Workspace
├── README.md                           # Development guide
├── shared/                             # Shared client libraries
│   ├── foundation-ws-client.js         # WebSocket client for Foundation
│   ├── vectra-styles.css               # Catppuccin theme
│   └── vectra-chart-utils.js           # Chart.js helpers
├── templates/                          # Artifact templates for dev agents
│   ├── artifact-template.html          # Base HTML template
│   └── artifact-template.js            # JS skeleton with data contract
├── tools/                              # Individual artifacts
│   ├── seed-bruteforce/                # Artifact 1: PRNG seed analysis
│   │   ├── index.html
│   │   ├── main.js
│   │   └── README.md
│   └── prediction-engine/              # Artifact 2: Bayesian predictor
│       ├── index.html
│       ├── main.js
│       └── components/
│           ├── equilibrium-tracker.js
│           ├── dynamic-weighter.js
│           ├── stochastic-oscillator.js
│           └── bayesian-forecaster.js
└── orchestrator/                       # Tab-based wrapper
    ├── index.html
    ├── orchestrator.js
    └── registry.json                   # Artifact registry
```

---

## Architecture

### Data Flow
```
rugs.fun WebSocket (via CDP)
    ↓
Foundation Service (normalizer.py)
    ↓
WebSocketBroadcaster (port 9000)
    ↓
┌───────────────────────────────────┐
│  Orchestrator (browser)           │
│  ↓ postMessage                    │
│  ┌───────────┬───────────────┐    │
│  │  iframe   │    iframe     │    │
│  │  Seed BF  │  Prediction   │    │
│  └───────────┴───────────────┘    │
└───────────────────────────────────┘
```

### Foundation Service Event Types (Normalized)

| Event Type | Source Event | Payload |
|------------|--------------|---------|
| `game.tick` | `gameStateUpdate` | `{game_id, tick, price, phase, active, rugged, ...}` |
| `player.state` | `playerUpdate` | `{balance, position_qty, avg_cost, pnl, ...}` |
| `connection.authenticated` | `usernameStatus` | `{username, status}` |
| `player.trade` | `standard/newTrade` | `{type, amount, price, qty, tick_index, ...}` |
| `sidebet.placed` | `currentSidebet` | `{amount, payout, start_tick, end_tick}` |
| `sidebet.result` | `currentSidebetResult` | `{won, payout, tick_index}` |

### Foundation Config

```python
# Default ports (env var overrides available)
FOUNDATION_PORT=9000        # WebSocket broadcaster
FOUNDATION_HTTP_PORT=9001   # Monitoring UI
CDP_PORT=9222               # Chrome DevTools Protocol
```

---

## Implementation Tasks

### Phase 0: Merge Foundation Service (Pre-requisite)

1. **Merge feature branch to main**
   ```bash
   git checkout main
   git merge feature/typescript-frontend-api
   ```

2. **Verify Foundation Service runs**
   ```bash
   python -m foundation.launcher
   # Should start:
   # - Chrome with rugs_bot profile
   # - WebSocket broadcaster on port 9000
   # - Monitoring UI on port 9001
   ```

### Phase 1: Shared Infrastructure (Day 1)

1. **Create directory structure**
   - `src/artifacts/` with subdirectories

2. **Build `foundation-ws-client.js`** (connects to Foundation Service)
   - WebSocket connection to `ws://localhost:9000/feed`
   - Automatic reconnection with backoff
   - Handles Foundation's normalized event format
   - Metrics tracking (latency, message count)

3. **Build `vectra-styles.css`**
   - Catppuccin Mocha theme
   - Standard artifact layout (header, main, footer)
   - Connection status indicator

4. **Create artifact templates**
   - `artifact-template.html` - standardized structure
   - `artifact-template.js` - event handling skeleton (uses Foundation events)

### Phase 2: Seed Bruteforce Tool (Day 2)

1. **Port seed analysis from PRNG CRAK**
   - Load `games_dataset.jsonl` (2,835 games)
   - Seed format detection (hex, timestamp, sequential)
   - Pattern correlation analysis

2. **Build UI**
   - Seed input field + file upload
   - Pattern selector (radio buttons)
   - Results table with highlighting
   - Progress bar for brute-force operations

3. **Add Web Workers for heavy computation**
   - Offload brute-force to background threads
   - Progress reporting back to main thread

### Phase 3: Prediction Engine (Day 3-4)

1. **Port Python components to JavaScript**

   **EquilibriumTracker** (from HAIKU lines 560-637):
   - EWMA equilibrium tracking
   - Regime detection (NORMAL, SUPPRESSED, INFLATED, VOLATILE)
   - Drift detection for long-term mean shift

   **DynamicWeighter** (from HAIKU lines 650-705):
   - Regime-based weight matrices
   - Volatility penalty calculation
   - Outlier sensitivity adjustment

   **StochasticOscillationModel** (from HAIKU lines 711-810):
   - Online AR(p) with RLS update
   - Adaptive order selection via AIC/BIC
   - Forecast with variance estimation

   **BayesianForecaster** (from HAIKU lines 821-899):
   - Kalman filter fusion
   - Multi-component prediction (mean-reversion + AR + peak effect)
   - Confidence interval calculation

2. **Build UI**
   - Real-time game state display
   - Prediction panel (final price, peak, duration with intervals)
   - Historical accuracy chart
   - Regime indicator

### Phase 4: Orchestrator (Day 5)

1. **Build tab-based wrapper**
   - Tab navigation buttons
   - Iframe management
   - Single Foundation WebSocket connection, relayed via postMessage

2. **Implement artifact registry**
   - `registry.json` with artifact metadata
   - Dynamic tab building from registry

3. **Serve via Foundation HTTP server (port 9001)**
   - Artifacts served alongside monitoring dashboard
   - OR add route to Flask server:
   ```python
   @app.route('/artifacts/<path:filename>')
   def serve_artifact(filename):
       return send_from_directory('../artifacts', filename)
   ```

---

## Key Files to Modify

| File | Change |
|------|--------|
| `src/recording_ui/app.py` | Add `/artifacts/` route (optional if using Foundation HTTP) |
| `src/foundation/http_server.py` | Add artifacts serving route |
| `src/recording_ui/templates/dashboard.html` | Add link to orchestrator |

## Key Files to Reference

| File | Purpose |
|------|---------|
| `src/foundation/broadcaster.py` | WebSocket broadcaster implementation |
| `src/foundation/normalizer.py` | Event normalization (rugs.fun -> Foundation types) |
| `src/foundation/config.py` | Configuration with env var overrides |
| `src/rugs_recordings/PRNG CRAK/HAIKU-CRITICAL-FINDINGS.md` | Prediction engine algorithms (lines 500-900) |
| `src/rugs_recordings/PRNG CRAK/prediction_engine/` | Existing Python implementations |
| `notebooks/bayesian_sidebet_analysis.py` | Bayesian model reference |

---

## Verification Plan

### Foundation Service Testing
```bash
# Start Foundation Service
cd /home/devops/Desktop/VECTRA-PLAYER
python -m foundation.launcher

# Verify services start:
# - Chrome opens to rugs.fun
# - WebSocket broadcaster on ws://localhost:9000/feed
# - Monitoring dashboard at http://localhost:9001
```

### Standalone Artifact Testing
```bash
# Open artifact directly (after Foundation running)
# Browser: http://localhost:9001/artifacts/tools/seed-bruteforce/index.html

# Verify in browser console:
# - WebSocket connects to ws://localhost:9000/feed
# - game.tick events appear
# - connection.authenticated confirms user
```

### Orchestrator Testing
```bash
# Open orchestrator
# Browser: http://localhost:9001/artifacts/orchestrator/index.html

# Verify:
# - Tabs switch correctly
# - Events reach both iframes via postMessage
# - Single WebSocket connection (check Network tab)
```

### Prediction Engine Validation
1. Load historical game data
2. Run backtested predictions
3. Compare predicted vs actual:
   - Final price MAE < 0.0050
   - Peak MAE < 2.0x
   - Duration MAE < 100 ticks

---

## Artifact Template Specification (for Dev Agents)

**Required Structure:**
```
tools/<artifact-name>/
├── index.html          # Uses artifact-template.html base
├── main.js             # Implements required hooks
└── README.md           # Documents data contract
```

**Required Hooks in main.js:**
```javascript
const ARTIFACT_CONFIG = {
    id: 'unique-id',
    name: 'Display Name',
    subscriptions: ['game_state']  // Events to receive
};

function initializeUI() { /* Setup DOM */ }
function processGameState(data) { /* Handle game_state */ }
function processLiveTick(tick, session) { /* Handle live_tick */ }
```

---

## Success Criteria

- [ ] Artifacts run standalone with live WebSocket data
- [ ] Orchestrator manages multiple artifacts in tabs
- [ ] Single WebSocket connection serves all artifacts
- [ ] Prediction engine produces real-time forecasts
- [ ] Seed bruteforce tool analyzes game seeds
- [ ] Documentation enables agent-based artifact creation

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| WebSocket disconnect | Auto-reconnect with exponential backoff |
| Iframe security | Same-origin policy (all from localhost:5000) |
| Memory bloat | Limit history buffers (max 1000 events) |
| Slow predictions | Web Workers for heavy computation |

---

## Execution Strategy: Tools, Skills & Sub-Agents

### Available Force Multipliers

| Resource | Purpose | When to Use |
|----------|---------|-------------|
| **@rugs-expert MCP** | Canonical rugs.fun knowledge | Event schemas, game mechanics validation |
| **context7 MCP** | Library documentation | JavaScript API references (Chart.js, WebSocket) |
| **TDD skill** | Test-first development | All new code - prevents bugs at source |
| **verify skill** | Evidence before claims | After each phase completion |
| **code-review skill** | Quality gate | Before merging any changes |
| **Plan subagent** | Architecture decisions | Complex design choices |
| **Explore subagent** | Codebase discovery | Finding existing patterns |
| **feature-dev:code-architect** | Component design | New artifact architecture |

### Verification Checkpoints

| Checkpoint | Trigger | Action |
|------------|---------|--------|
| **VER-1** | After Foundation merge | Run `python -m foundation.launcher` |
| **VER-2** | After docs update | Read updated files, verify accuracy |
| **VER-3** | After each artifact | Open in browser, verify WS connection |
| **VER-4** | After orchestrator | All artifacts work in tabs |
| **VER-5** | Final | Full integration test |

---

*Created: 2026-01-17 | Implementation In Progress*
