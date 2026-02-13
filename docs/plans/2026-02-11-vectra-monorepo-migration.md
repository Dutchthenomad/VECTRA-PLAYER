# VECTRA Monorepo Migration Plan

**Date:** 2026-02-11
**Status:** Ready for execution
**Goal:** Extract the production system into a clean `~/Desktop/vectra/` monorepo

---

## Context

VECTRA-BOILERPLATE has accumulated multiple generations of code (REPLAYER -> VECTRA-PLAYER -> VECTRA-BOILERPLATE). Rather than surgically cleaning it, we extract the **final production system** into a new clean monorepo. VECTRA-BOILERPLATE becomes a read-only archive.

### Decisions Made

| Decision | Choice |
|----------|--------|
| Legacy code in `src/` | Keep in archive, don't touch |
| Project structure | Monorepo with all services |
| Deployment target | All local (Docker Compose) first, VPS later |
| Pipeline source of truth | `rugs-data-pipeline/` (has 637 tests) |
| Game data (6.6GB) | Stays in archive, not copied |
| Excalidraw system map | Copied to new project, continues evolving |

---

## Target Directory Structure

```
~/Desktop/vectra/
├── docker-compose.yml              # Unified orchestration (all services)
├── .env                            # Port assignments + environment
├── .env.example                    # Template for .env
├── .gitignore
├── CLAUDE.md                       # Agent instructions (rewritten for new project)
├── README.md
│
├── services/
│   ├── nexus-ui/                   # React frontend + nginx reverse proxy
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml      # Standalone dev compose
│   │   ├── nginx/default.conf
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── .env.local
│   │   └── src/
│   │       ├── index.html
│   │       ├── index.tsx
│   │       ├── index.css
│   │       ├── services.ts
│   │       ├── constants.ts
│   │       ├── types.ts
│   │       ├── utils.ts
│   │       └── components/
│   │           ├── Icons.tsx
│   │           ├── SideDrawer.tsx
│   │           ├── ArtifactCard.tsx
│   │           └── DottedGlowBackground.tsx
│   │
│   ├── foundation/                 # Chrome CDP -> WebSocket broadcaster
│   │   ├── Dockerfile              # NEW - needs creation
│   │   ├── requirements.txt        # NEW - needs creation
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── launcher.py
│   │       ├── service_manager.py
│   │       ├── http_server.py
│   │       ├── broadcaster.py
│   │       ├── normalizer.py
│   │       ├── client.py
│   │       ├── subscriber.py
│   │       ├── events.py
│   │       ├── connection.py
│   │       ├── runner.py
│   │       ├── service.py
│   │       └── static/
│   │           ├── index.html
│   │           ├── monitor.html
│   │           ├── monitor.js
│   │           ├── control-panel.css
│   │           └── styles.css
│   │
│   ├── v2-explorer/                # PRNG analysis / replay tool
│   │   ├── Dockerfile
│   │   ├── .dockerignore
│   │   ├── server.py
│   │   ├── modules/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── sidebet.py
│   │   └── static/
│   │       └── demo-trace.html
│   │
│   ├── rugs-feed/                  # WebSocket ingest + PRNG tracking
│   │   ├── Dockerfile
│   │   ├── manifest.json
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   ├── .env.example
│   │   ├── .dockerignore
│   │   ├── config/
│   │   ├── src/
│   │   └── tests/                  # 22 tests
│   │
│   ├── rugs-sanitizer/             # Dedup & validation
│   │   ├── Dockerfile
│   │   ├── manifest.json
│   │   ├── requirements.txt
│   │   ├── SUBSCRIBER-GUIDE.md
│   │   ├── config/
│   │   ├── src/
│   │   └── tests/                  # 106 tests
│   │
│   ├── feature-extractor/          # Feature vector computation
│   │   ├── Dockerfile
│   │   ├── manifest.json
│   │   ├── requirements.txt
│   │   ├── config/
│   │   ├── src/
│   │   └── tests/                  # 69 tests
│   │
│   ├── decision-engine/            # Strategy + mode selection
│   │   ├── Dockerfile
│   │   ├── manifest.json
│   │   ├── requirements.txt
│   │   ├── config/
│   │   ├── src/
│   │   └── tests/                  # 362 tests
│   │
│   ├── execution/                  # Trade execution
│   │   ├── Dockerfile
│   │   ├── manifest.json
│   │   ├── requirements.txt
│   │   ├── config/
│   │   ├── src/
│   │   └── tests/                  # 70 tests
│   │
│   ├── ui/                         # Pipeline UI service
│   │   ├── Dockerfile
│   │   ├── manifest.json
│   │   ├── requirements.txt
│   │   ├── config/
│   │   ├── src/
│   │   └── tests/                  # 4 tests
│   │
│   └── monitoring/                 # Health aggregation
│       ├── Dockerfile
│       ├── manifest.json
│       ├── requirements.txt
│       ├── config/
│       ├── src/
│       └── tests/                  # 3 tests
│
├── artifacts/                      # HTML modules served via Nexus UI
│   ├── shared/
│   │   ├── foundation-ws-client.js
│   │   ├── foundation-state.js
│   │   └── vectra-styles.css
│   ├── orchestrator/
│   │   ├── index.html
│   │   ├── orchestrator.js
│   │   └── registry.json
│   ├── minimal-trading/
│   │   ├── manifest.json
│   │   ├── index.html
│   │   ├── app.js
│   │   └── styles.css
│   └── recording-control/
│       ├── manifest.json
│       ├── index.html
│       └── app.js
│
├── scripts/
│   ├── start.sh                    # One-command startup
│   ├── validate_ports.py           # Port conflict detection
│   └── verify_migration.sh         # NEW - 3-tier migration verification
│
├── tests/
│   ├── verify_contracts.py         # Cross-service envelope contract tests
│   └── integration/                # Future: cross-service integration tests
│
├── data/                           # Runtime data (gitignored, Docker volumes)
│   ├── .gitkeep
│   ├── risk/
│   ├── models/
│   └── monitoring/
│
├── docs/
│   ├── nexus-ui-layout-v2.excalidraw   # System map (living document)
│   ├── rosetta-stone/
│   │   └── ROSETTA-STONE.md
│   ├── specs/
│   │   ├── PORT-ALLOCATION-SPEC.md
│   │   ├── MODULE-EXTENSION-SPEC.md
│   │   └── FOUNDATION-API-CONTRACT.md
│   └── CHROME_PROFILE_SETUP.md
│
└── .claude/
    ├── settings.local.json
    └── hookify.*.local.md          # 13 safety gate rules
```

---

## Phase 1: Create Directory Structure

```bash
# Create the new project root
mkdir -p ~/Desktop/vectra

# Create all subdirectories
mkdir -p ~/Desktop/vectra/{services,artifacts,scripts,tests,data,docs,.claude}
mkdir -p ~/Desktop/vectra/tests/integration
mkdir -p ~/Desktop/vectra/data/{risk,models,monitoring}
mkdir -p ~/Desktop/vectra/docs/{rosetta-stone,specs}
mkdir -p ~/Desktop/vectra/artifacts/{shared,orchestrator,minimal-trading,recording-control}

touch ~/Desktop/vectra/data/.gitkeep
```

---

## Phase 2: Copy Pipeline Services (from rugs-data-pipeline)

**Source:** `/home/devops/rugs-data-pipeline/`

```bash
PIPE=~/rugs-data-pipeline
DEST=~/Desktop/vectra

# Copy all 7 pipeline services
for svc in rugs-feed rugs-sanitizer feature-extractor decision-engine execution ui monitoring; do
    cp -r "$PIPE/services/$svc" "$DEST/services/$svc"
done

# Copy contract tests
cp "$PIPE/verify_contracts.py" "$DEST/tests/verify_contracts.py"

# Copy the .env as template
cp "$PIPE/.env" "$DEST/.env.example"

# Copy pipeline docker-compose files as reference
cp "$PIPE/docker-compose.yml" "$DEST/docker-compose.pipeline-base.yml.ref"
cp "$PIPE/docker-compose.bot.yml" "$DEST/docker-compose.pipeline-bot.yml.ref"
```

**Clean up copied dirs (remove __pycache__, .pyc, etc.):**

```bash
find "$DEST/services" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$DEST/services" -name "*.pyc" -delete 2>/dev/null
find "$DEST/services" -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
```

---

## Phase 3: Copy Nexus UI (from VECTRA-BOILERPLATE)

**Source:** `/home/devops/Desktop/VECTRA-BOILERPLATE/services/nexus-ui/`

```bash
SRC=~/Desktop/VECTRA-BOILERPLATE
DEST=~/Desktop/vectra

# Copy entire nexus-ui service
cp -r "$SRC/services/nexus-ui" "$DEST/services/nexus-ui"
```

---

## Phase 4: Copy Foundation Service (from VECTRA-BOILERPLATE)

**Source:** `/home/devops/Desktop/VECTRA-BOILERPLATE/src/foundation/`

Foundation needs to become a proper service with its own Dockerfile.

```bash
SRC=~/Desktop/VECTRA-BOILERPLATE
DEST=~/Desktop/vectra

# Create foundation service directory and copy source
mkdir -p "$DEST/services/foundation/src"
cp -r "$SRC/src/foundation/"* "$DEST/services/foundation/src/"

# Remove __pycache__ from foundation
find "$DEST/services/foundation" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

**NEW FILES TO CREATE** (foundation Dockerfile and requirements.txt - see Phase 7 below).

---

## Phase 5: Copy v2-explorer (from VECTRA-BOILERPLATE)

**Source:** `/home/devops/Desktop/VECTRA-BOILERPLATE/tools/v2-explorer/`

```bash
SRC=~/Desktop/VECTRA-BOILERPLATE
DEST=~/Desktop/vectra

# Copy v2-explorer
cp -r "$SRC/tools/v2-explorer" "$DEST/services/v2-explorer"

# Clean __pycache__
find "$DEST/services/v2-explorer" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

---

## Phase 6: Copy Artifacts, Docs, Config, Scripts

```bash
SRC=~/Desktop/VECTRA-BOILERPLATE
DEST=~/Desktop/vectra

# --- Artifacts ---
cp "$SRC/src/artifacts/shared/foundation-ws-client.js" "$DEST/artifacts/shared/"
cp "$SRC/src/artifacts/shared/foundation-state.js"     "$DEST/artifacts/shared/"
cp "$SRC/src/artifacts/shared/vectra-styles.css"        "$DEST/artifacts/shared/"

# Orchestrator
cp "$SRC/src/artifacts/orchestrator/index.html"       "$DEST/artifacts/orchestrator/"
cp "$SRC/src/artifacts/orchestrator/orchestrator.js"  "$DEST/artifacts/orchestrator/"
cp "$SRC/src/artifacts/orchestrator/registry.json"    "$DEST/artifacts/orchestrator/"

# Minimal trading artifact
cp "$SRC/src/artifacts/tools/minimal-trading/"*.{html,js,css,json} "$DEST/artifacts/minimal-trading/" 2>/dev/null
# If glob fails, copy individually:
# cp "$SRC/src/artifacts/tools/minimal-trading/index.html" "$DEST/artifacts/minimal-trading/"
# cp "$SRC/src/artifacts/tools/minimal-trading/app.js" "$DEST/artifacts/minimal-trading/"
# cp "$SRC/src/artifacts/tools/minimal-trading/styles.css" "$DEST/artifacts/minimal-trading/"
# cp "$SRC/src/artifacts/tools/minimal-trading/manifest.json" "$DEST/artifacts/minimal-trading/"

# Recording control artifact
cp "$SRC/src/artifacts/tools/recording-control/"*.{html,js,json} "$DEST/artifacts/recording-control/" 2>/dev/null

# --- Docs ---
cp "$SRC/docs/nexus-ui-layout-v2.excalidraw"          "$DEST/docs/"
cp -r "$SRC/docs/rosetta-stone/ROSETTA-STONE.md"       "$DEST/docs/rosetta-stone/"
cp "$SRC/docs/specs/PORT-ALLOCATION-SPEC.md"           "$DEST/docs/specs/"
cp "$SRC/docs/specs/MODULE-EXTENSION-SPEC.md"          "$DEST/docs/specs/"
cp "$SRC/docs/specs/FOUNDATION-API-CONTRACT.md"        "$DEST/docs/specs/"
cp "$SRC/docs/CHROME_PROFILE_SETUP.md"                 "$DEST/docs/"

# --- Scripts ---
cp "$SRC/scripts/start.sh"           "$DEST/scripts/"
cp "$SRC/scripts/validate_ports.py"  "$DEST/scripts/"

# --- Hookify Rules (all 13) ---
cp "$SRC/.claude/hookify."*.local.md  "$DEST/.claude/"
cp "$SRC/.claude/settings.local.json" "$DEST/.claude/"

# --- Root Config ---
cp "$SRC/.gitignore" "$DEST/.gitignore"
```

---

## Phase 7: Create New Files

These files don't exist in any source and must be created fresh.

### 7a. `vectra/.env`

```env
# VECTRA Service Ports
FEED_PORT=9016
SANITIZER_PORT=9017
FEATURE_PORT=9018
ENGINE_PORT=9019
EXECUTION_PORT=9020
MONITORING_PORT=9021

# Infrastructure
FOUNDATION_WS_PORT=9000
FOUNDATION_HTTP_PORT=9001
CDP_PORT=9222
NEXUS_PORT=3000
EXPLORER_PORT=9040

# VPS (for external service references)
VPS_HOST=72.62.160.2
GRAFANA_PORT=3100
METABASE_PORT=3101
UPTIME_KUMA_PORT=3102
DOZZLE_PORT=8900
RABBITMQ_PORT=5672
RABBITMQ_MGMT_PORT=15672
TIMESCALEDB_PORT=5433

# Logging
LOG_LEVEL=INFO
```

### 7b. `vectra/docker-compose.yml`

Merge the two pipeline compose files + add nexus-ui, foundation, v2-explorer:

```yaml
services:
  # ─── Frontend ─────────────────────────────────────────
  nexus-ui:
    build:
      context: ./services/nexus-ui
      dockerfile: Dockerfile
    container_name: vectra-nexus-ui
    restart: unless-stopped
    ports:
      - "${NEXUS_PORT:-3000}:80"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:80/"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - vectra
    extra_hosts:
      - "host.docker.internal:host-gateway"

  # ─── Core Services ───────────────────────────────────
  v2-explorer:
    build:
      context: ./services/v2-explorer
      dockerfile: Dockerfile
    container_name: vectra-v2-explorer
    restart: unless-stopped
    ports:
      - "${EXPLORER_PORT:-9040}:9040"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9040/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - vectra

  # ─── Pipeline: Ingest Layer ──────────────────────────
  rugs-feed:
    build:
      context: ./services/rugs-feed
      dockerfile: Dockerfile
    container_name: vectra-rugs-feed
    restart: unless-stopped
    ports:
      - "${FEED_PORT:-9016}:9016"
    volumes:
      - ./services/rugs-feed/config:/app/config:ro
      - ./data:/data
    environment:
      - RUGS_BACKEND_URL=${RUGS_BACKEND_URL:-https://backend.rugs.fun}
      - PORT=9016
      - HOST=0.0.0.0
      - STORAGE_PATH=/data/rugs_feed.db
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9016/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  # ─── Pipeline: Processing Layer ──────────────────────
  rugs-sanitizer:
    build:
      context: ./services/rugs-sanitizer
      dockerfile: Dockerfile
    container_name: vectra-rugs-sanitizer
    restart: unless-stopped
    ports:
      - "${SANITIZER_PORT:-9017}:9017"
    volumes:
      - ./services/rugs-sanitizer/config:/app/config:ro
    environment:
      - UPSTREAM_URL=ws://rugs-feed:9016/feed
      - PORT=9017
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      rugs-feed:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9017/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  feature-extractor:
    build:
      context: ./services/feature-extractor
      dockerfile: Dockerfile
    container_name: vectra-feature-extractor
    restart: unless-stopped
    ports:
      - "${FEATURE_PORT:-9018}:9018"
    volumes:
      - ./services/feature-extractor/config:/app/config:ro
    environment:
      - UPSTREAM_URL=ws://rugs-sanitizer:9017/feed/game
      - PORT=9018
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      rugs-sanitizer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9018/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  # ─── Pipeline: Decision Layer ────────────────────────
  decision-engine:
    build:
      context: ./services/decision-engine
      dockerfile: Dockerfile
    container_name: vectra-decision-engine
    restart: unless-stopped
    ports:
      - "${ENGINE_PORT:-9019}:9019"
    volumes:
      - ./services/decision-engine/config:/app/config:ro
      - ./data/risk:/data
      - ./data/models:/models:ro
    environment:
      - UPSTREAM_URL=ws://feature-extractor:9018/feed/features
      - PORT=9019
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      feature-extractor:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9019/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  # ─── Pipeline: Execution Layer ───────────────────────
  execution:
    build:
      context: ./services/execution
      dockerfile: Dockerfile
    container_name: vectra-execution
    restart: unless-stopped
    ports:
      - "9022:9022"
    volumes:
      - ./services/execution/config:/app/config:ro
    environment:
      - UPSTREAM_URL=ws://decision-engine:9019/feed/recommendations
      - PORT=9022
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      decision-engine:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9022/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  ui:
    build:
      context: ./services/ui
      dockerfile: Dockerfile
    container_name: vectra-pipeline-ui
    restart: unless-stopped
    ports:
      - "${EXECUTION_PORT:-9020}:9020"
    volumes:
      - ./services/ui/config:/app/config:ro
    environment:
      - UPSTREAM_URL=ws://decision-engine:9019/feed/recommendations
      - FEATURE_URL=ws://feature-extractor:9018/feed/features
      - SANITIZER_URL=ws://rugs-sanitizer:9017/feed/game
      - PORT=9020
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      decision-engine:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  # ─── Pipeline: Observability ─────────────────────────
  monitoring:
    build:
      context: ./services/monitoring
      dockerfile: Dockerfile
    container_name: vectra-monitoring
    restart: on-failure
    ports:
      - "${MONITORING_PORT:-9021}:9021"
    volumes:
      - ./services/monitoring/config:/app/config:ro
      - ./data/monitoring:/data
    environment:
      - UPSTREAM_URL=ws://decision-engine:9019/feed/recommendations
      - SANITIZER_STATS_URL=http://rugs-sanitizer:9017/stats
      - FEATURE_STATS_URL=http://feature-extractor:9018/stats
      - ENGINE_STATS_URL=http://decision-engine:9019/stats
      - PORT=9021
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      decision-engine:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9021/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - vectra
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

networks:
  vectra:
    name: vectra
    driver: bridge
```

> **Note:** Foundation service runs outside Docker (needs local Chrome + Phantom wallet). Start separately with `python -m src.launcher` from `services/foundation/`.

### 7c. `vectra/services/foundation/requirements.txt`

```
aiohttp>=3.9.0
websockets>=12.0
```

### 7d. `vectra/services/foundation/Dockerfile`

```dockerfile
# Foundation runs OUTSIDE Docker in production (needs Chrome CDP),
# but this Dockerfile exists for future headless/VPS deployment.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
EXPOSE 9000 9001

CMD ["python", "-m", "src.launcher"]
```

### 7e. `vectra/scripts/verify_migration.sh`

```bash
#!/usr/bin/env bash
# VECTRA Migration Verification - 3 Tier
# Run from vectra/ root directory
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
SKIP=0

pass() { echo -e "  ${GREEN}PASS${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}FAIL${NC} $1"; ((FAIL++)); }
skip() { echo -e "  ${YELLOW}SKIP${NC} $1"; ((SKIP++)); }

echo "============================================"
echo " VECTRA Migration Verification"
echo " $(date)"
echo "============================================"
echo ""

# ──────────────────────────────────────────────
# TIER 0: Structure Verification
# ──────────────────────────────────────────────
echo "── TIER 0: Directory Structure ──"

REQUIRED_DIRS=(
    "services/nexus-ui/src"
    "services/nexus-ui/nginx"
    "services/foundation/src"
    "services/v2-explorer/modules"
    "services/rugs-feed/src"
    "services/rugs-feed/tests"
    "services/rugs-sanitizer/src"
    "services/rugs-sanitizer/tests"
    "services/feature-extractor/src"
    "services/feature-extractor/tests"
    "services/decision-engine/src"
    "services/decision-engine/tests"
    "services/execution/src"
    "services/execution/tests"
    "services/ui/src"
    "services/monitoring/src"
    "artifacts/shared"
    "artifacts/orchestrator"
    "docs/rosetta-stone"
    "docs/specs"
    ".claude"
    "scripts"
    "tests"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        pass "$dir/"
    else
        fail "$dir/ MISSING"
    fi
done

REQUIRED_FILES=(
    "docker-compose.yml"
    ".env"
    ".gitignore"
    "artifacts/shared/foundation-ws-client.js"
    "artifacts/shared/foundation-state.js"
    "artifacts/shared/vectra-styles.css"
    "docs/nexus-ui-layout-v2.excalidraw"
    "docs/rosetta-stone/ROSETTA-STONE.md"
    "docs/specs/PORT-ALLOCATION-SPEC.md"
    "docs/specs/MODULE-EXTENSION-SPEC.md"
    "docs/specs/FOUNDATION-API-CONTRACT.md"
    "docs/CHROME_PROFILE_SETUP.md"
    "scripts/verify_migration.sh"
    "scripts/validate_ports.py"
    "tests/verify_contracts.py"
    "services/foundation/Dockerfile"
    "services/foundation/requirements.txt"
    "services/nexus-ui/Dockerfile"
    "services/nexus-ui/nginx/default.conf"
    "services/nexus-ui/src/services.ts"
    "services/v2-explorer/Dockerfile"
)

for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
        pass "$f"
    else
        fail "$f MISSING"
    fi
done

echo ""

# ──────────────────────────────────────────────
# TIER 1: Unit Tests (per service)
# ──────────────────────────────────────────────
echo "── TIER 1: Unit Tests ──"

declare -A SERVICES=(
    ["rugs-feed"]=22
    ["rugs-sanitizer"]=106
    ["feature-extractor"]=69
    ["decision-engine"]=362
    ["execution"]=70
    ["ui"]=4
    ["monitoring"]=3
)

for svc in "${!SERVICES[@]}"; do
    expected=${SERVICES[$svc]}
    svc_dir="services/$svc"

    if [ ! -d "$svc_dir/tests" ]; then
        fail "$svc: no tests/ directory"
        continue
    fi

    echo -e "  Testing ${YELLOW}$svc${NC} (expecting ~$expected tests)..."

    # Create temp venv if needed, or use system python
    if command -v python3 &>/dev/null; then
        cd "$svc_dir"
        if python3 -m pytest tests/ -v --tb=short -q 2>/tmp/vectra_test_${svc}.log; then
            ACTUAL=$(grep -oP '\d+ passed' /tmp/vectra_test_${svc}.log | head -1 | grep -oP '\d+')
            pass "$svc: ${ACTUAL:-?} tests passed"
        else
            fail "$svc: tests failed (see /tmp/vectra_test_${svc}.log)"
        fi
        cd - >/dev/null
    else
        skip "$svc: python3 not found"
    fi
done

echo ""

# ──────────────────────────────────────────────
# TIER 2: Contract Tests
# ──────────────────────────────────────────────
echo "── TIER 2: Contract Tests ──"

if [ -f "tests/verify_contracts.py" ]; then
    echo "  Running envelope contract verification..."
    if python3 tests/verify_contracts.py 2>/tmp/vectra_contracts.log; then
        pass "Cross-service envelope contracts verified"
    else
        fail "Contract verification failed (see /tmp/vectra_contracts.log)"
    fi
else
    fail "verify_contracts.py not found"
fi

echo ""

# ──────────────────────────────────────────────
# TIER 3: Docker Compose Build
# ──────────────────────────────────────────────
echo "── TIER 3: Docker Compose Build ──"

if command -v docker &>/dev/null; then
    echo "  Building all services (this may take a few minutes)..."
    if docker compose build 2>/tmp/vectra_build.log; then
        pass "All Docker images built successfully"
    else
        fail "Docker build failed (see /tmp/vectra_build.log)"
    fi
else
    skip "Docker not available"
fi

echo ""

# ──────────────────────────────────────────────
# TIER 3b: Docker Health Check (optional, requires running stack)
# ──────────────────────────────────────────────
echo "── TIER 3b: Health Endpoints (run 'docker compose up -d' first) ──"

HEALTH_ENDPOINTS=(
    "localhost:9016/health|rugs-feed"
    "localhost:9017/health|rugs-sanitizer"
    "localhost:9018/health|feature-extractor"
    "localhost:9019/health|decision-engine"
    "localhost:9020/health|ui"
    "localhost:9021/health|monitoring"
    "localhost:3000|nexus-ui"
    "localhost:9040/health|v2-explorer"
    "localhost:9001|foundation"
)

for entry in "${HEALTH_ENDPOINTS[@]}"; do
    url="${entry%%|*}"
    name="${entry##*|}"
    if curl -sf "http://$url" >/dev/null 2>&1; then
        pass "$name -> http://$url"
    else
        skip "$name -> http://$url (not running)"
    fi
done

echo ""

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
echo "============================================"
echo -e " Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$SKIP skipped${NC}"
echo "============================================"

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}Migration verification INCOMPLETE - fix failures above${NC}"
    exit 1
else
    echo -e "${GREEN}Migration verification PASSED${NC}"
    exit 0
fi
```

### 7f. `vectra/README.md`

```markdown
# VECTRA

Unified trading system for rugs.fun — monorepo containing all services.

## Quick Start

```bash
# Copy .env template and adjust
cp .env.example .env

# Start Foundation (needs local Chrome + Phantom wallet)
cd services/foundation && python -m src.launcher

# Start all Docker services
docker compose up -d

# Open Nexus UI
open http://localhost:3000
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| nexus-ui | 3000 | React frontend + nginx proxy |
| foundation | 9000/9001 | Chrome CDP -> WebSocket broadcaster |
| v2-explorer | 9040 | PRNG analysis / replay engine |
| rugs-feed | 9016 | WebSocket ingest + PRNG tracking |
| rugs-sanitizer | 9017 | Dedup & validation |
| feature-extractor | 9018 | Feature vector computation |
| decision-engine | 9019 | Strategy + mode selection |
| ui (pipeline) | 9020 | Pipeline UI aggregation |
| monitoring | 9021 | Health aggregation |
| execution | 9022 | Trade execution |

## Verification

```bash
./scripts/verify_migration.sh
```

## Architecture

See `docs/nexus-ui-layout-v2.excalidraw` for the complete system map.
```

---

## Phase 8: Initialize Git Repository

```bash
cd ~/Desktop/vectra

git init
git add .
git commit -m "Initial commit: VECTRA monorepo

Consolidated from:
- VECTRA-BOILERPLATE (nexus-ui, foundation, artifacts, docs)
- rugs-data-pipeline (7 pipeline services, 637 tests)

Services: nexus-ui, foundation, v2-explorer, rugs-feed,
rugs-sanitizer, feature-extractor, decision-engine,
execution, ui, monitoring

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 9: Run Verification

```bash
cd ~/Desktop/vectra

# Make verify script executable
chmod +x scripts/verify_migration.sh

# Run full verification
./scripts/verify_migration.sh
```

### Expected Results

| Tier | Check | Expected |
|------|-------|----------|
| 0 | Directory structure | All dirs/files present |
| 1 | rugs-feed tests | 22 passed |
| 1 | rugs-sanitizer tests | 106 passed |
| 1 | feature-extractor tests | 69 passed |
| 1 | decision-engine tests | 362 passed |
| 1 | execution tests | 70 passed |
| 1 | ui tests | 4 passed |
| 1 | monitoring tests | 3 passed |
| 2 | Contract verification | 4 contracts pass |
| 3 | Docker build | All images build |
| 3b | Health endpoints | Pass after `docker compose up` |

**Total expected: ~636 unit tests + 4 contracts + 10 health checks**

---

## Post-Migration Checklist

- [ ] All Tier 0 structure checks pass
- [ ] All Tier 1 unit tests pass (636+ tests)
- [ ] Tier 2 contract tests pass
- [ ] Tier 3 Docker images build
- [ ] `docker compose up -d` starts all services
- [ ] Nexus UI loads at http://localhost:3000
- [ ] v2-explorer loads at http://localhost:9040
- [ ] Foundation starts manually and serves http://localhost:9001
- [ ] Pipeline chain connects: feed -> sanitizer -> extractor -> engine
- [ ] CLAUDE.md rewritten for new project structure
- [ ] Git repo initialized with initial commit
- [ ] Create GitHub repo and push

---

## Execution Notes

**Order matters:** Run phases 1-6 (copy), then 7 (create new files), then 8 (git init), then 9 (verify).

**Foundation service** runs outside Docker because it needs local Chrome with the Phantom wallet. The Dockerfile is provided for future headless/VPS deployment.

**The `ui` service** (port 9020) from the pipeline is the pipeline's own aggregation UI — distinct from `nexus-ui` (port 3000) which is the main frontend shell.

**The `execution` service** (port 9022) exists in the pipeline repo as a separate service. Port adjusted to 9022 to avoid conflict with `ui` on 9020.

**VECTRA-BOILERPLATE** remains untouched as the archive. No files are deleted or modified there.
