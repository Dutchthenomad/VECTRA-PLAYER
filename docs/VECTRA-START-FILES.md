# VECTRA Start - Files and Dependencies

All files, folders, and scripts used when running `./vectra start`.

---

## Entry Point

```
./vectra                          # Main launcher script (bash)
```

---

## Runtime Files (Created/Used)

| File | Purpose |
|------|---------|
| `.venv/` | Python virtual environment |
| `.vectra.log` | Foundation service logs |
| `.vectra.pid` | Foundation process ID file |

---

## Foundation Service (`python -m foundation.launcher`)

### Core Python Modules

```
src/foundation/
├── __init__.py              # Package init
├── launcher.py              # Main entry point - starts all services
├── config.py                # Configuration (ports, paths, etc.)
├── broadcaster.py           # WebSocket broadcaster (port 9000)
├── http_server.py           # HTTP server + Control Panel (port 9001)
├── normalizer.py            # Event normalization (rugs.fun → Foundation types)
├── events.py                # Event type definitions
├── client.py                # WebSocket client for rugs.fun
├── connection.py            # Connection management
├── runner.py                # Async runner utilities
├── service.py               # Base service class
├── service_manager.py       # Service lifecycle management
└── subscriber.py            # Base subscriber class
```

### Static Files (Control Panel UI)

```
src/foundation/static/
├── index.html               # Control Panel dashboard
├── monitor.html             # System monitor view
├── monitor.js               # Monitor JavaScript
├── styles.css               # Base styles
└── control-panel.css        # Control Panel specific styles
```

---

## Browser Automation (CDP Integration)

```
src/browser/
├── __init__.py              # Package init
├── manager.py               # CDP Browser Manager (main)
├── executor.py              # Trade execution via browser
├── automation.py            # Browser automation utilities
├── bridge.py                # Browser bridge abstraction
├── profiles.py              # Chrome profile management
├── cdp/
│   ├── __init__.py
│   └── launcher.py          # CDP launcher (legacy)
└── dom/
    ├── __init__.py
    ├── selectors.py         # DOM selectors for rugs.fun
    └── timing.py            # Timing metrics
```

---

## HTML Artifacts (Served via HTTP)

### Shared Resources

```
src/artifacts/shared/
├── foundation-ws-client.js  # WebSocket client for artifacts
├── foundation-state.js      # Centralized state management
└── vectra-styles.css        # Shared CSS variables/styles
```

### Minimal Trading (Bot UI)

```
src/artifacts/tools/minimal-trading/
├── index.html               # Bot Control Panel UI
├── app.js                   # BotController + MinimalTradingApp
├── styles.css               # Bot panel styles
├── manifest.json            # Artifact metadata
└── README.md                # Documentation
```

### Recording Control

```
src/artifacts/tools/recording-control/
├── index.html               # Recording control UI
├── app.js                   # Recording control logic
└── manifest.json            # Artifact metadata
```

### Prediction Engine

```
src/artifacts/tools/prediction-engine/
├── index.html               # Prediction UI
├── main.js                  # Main entry
├── README.md                # Documentation
└── components/
    ├── bayesian-forecaster.js
    ├── dynamic-weighter.js
    ├── equilibrium-tracker.js
    └── stochastic-oscillator.js
```

### Seed Bruteforce

```
src/artifacts/tools/seed-bruteforce/
├── index.html               # Seed analysis UI
├── main.js                  # Bruteforce logic
└── README.md                # Documentation
```

### Artifact Templates

```
src/artifacts/templates/
├── artifact-template.html   # HTML template for new artifacts
└── artifact-template.js     # JS template for new artifacts
```

### Orchestrator

```
src/artifacts/orchestrator/
├── index.html               # Orchestrator UI
├── orchestrator.js          # Orchestration logic
└── registry.json            # Artifact registry
```

---

## Optional Services (Not Auto-Started)

### Recording Service

```
services/recording/
├── manifest.json            # Service metadata
├── start.sh                 # Start script
├── docker-compose.yml       # Docker configuration
├── Dockerfile               # Container build
├── requirements.txt         # Python dependencies
├── README.md                # Documentation
├── config/
│   ├── config.yaml          # Service config
│   ├── recording_state.json # Recording state
│   └── seen_games.json      # Deduplication state
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── api.py               # REST API
│   ├── subscriber.py        # Foundation subscriber
│   ├── storage.py           # Parquet storage
│   └── dedup.py             # Deduplication logic
└── tests/
    ├── __init__.py
    ├── test_api.py
    └── test_subscriber.py
```

---

## Configuration Files

```
pyproject.toml               # Python project config + dependencies
```

---

## Ports Used

| Port | Service | Purpose |
|------|---------|---------|
| 9000 | Foundation WS | WebSocket broadcaster |
| 9001 | Foundation HTTP | Control Panel + API |
| 9222 | Chrome CDP | Browser automation |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `FOUNDATION_PORT` | 9000 | WebSocket port |
| `FOUNDATION_HTTP_PORT` | 9001 | HTTP port |
| `CDP_PORT` | 9222 | Chrome DevTools Protocol port |

---

## Startup Sequence

1. `./vectra start` executed
2. Check/create `.venv/` virtual environment
3. Activate venv, install dependencies from `pyproject.toml`
4. Kill existing Chrome processes (unless `--keep-chrome`)
5. Validate ports 9000, 9001 are free
6. Start `python -m foundation.launcher`
   - Foundation launcher starts:
     - Chrome with CDP on port 9222
     - WebSocket broadcaster on port 9000
     - HTTP server on port 9001
     - Connects to rugs.fun WebSocket
7. Wait for `/health` endpoint to return healthy
8. Display status and tail logs

---

## File Count Summary

| Category | Count |
|----------|-------|
| Foundation Python | 13 files |
| Foundation Static | 5 files |
| Browser Module | 11 files |
| Artifacts Shared | 3 files |
| Artifact Tools | 18 files |
| Recording Service | 17 files |
| **Total** | ~67 files |

---

*Generated: January 26, 2026*
