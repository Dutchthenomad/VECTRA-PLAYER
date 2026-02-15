# VECTRA-BOILERPLATE Service Registration Specification

**Status:** CANONICAL | **Version:** 1.0.0 | **Date:** 2026-01-24

---

## Purpose

This specification defines the requirements for registering services with the VECTRA Service Manager. All services in `services/<name>/` must comply with this spec to be managed by the unified launcher.

**This document is referenced by CLAUDE.md and is binding on all AI agents and human developers.**

---

## Service Manifest

Every service in `services/<name>/` MUST have a `manifest.json` file with the following structure:

```json
{
  "name": "service-name",
  "version": "1.0.0",
  "description": "Brief description of what this service does",
  "port": 9010,
  "health_endpoint": "/health",
  "start_command": "python -m src.main",
  "working_dir": "services/service-name",
  "requires_foundation": true,
  "events_consumed": ["game.tick", "player.state"],
  "events_emitted": [],
  "dependencies": []
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique service identifier (must match directory name) |
| `version` | string | Semantic version (e.g., "1.0.0") |
| `description` | string | Human-readable description (max 200 chars) |
| `port` | integer | Port number (MUST be allocated in PORT-ALLOCATION-SPEC) |
| `health_endpoint` | string | Health check path (e.g., "/health") |
| `start_command` | string | Command to start the service (relative to working_dir) |
| `working_dir` | string | Relative path from project root to service directory |
| `requires_foundation` | boolean | Whether service needs Foundation WebSocket feed |
| `events_consumed` | array | Foundation event types this service subscribes to |
| `events_emitted` | array | Event types this service produces (for documentation) |
| `dependencies` | array | Other service names that must start first |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Service author/team |
| `created` | string | Creation date (YYYY-MM-DD) |
| `docker` | object | Docker configuration (if containerized) |
| `storage` | object | Storage configuration |
| `features` | object | Feature flags |

---

## Port Allocation Enforcement

### Validation Rules

1. Service Manager reads `docs/specs/PORT-ALLOCATION-SPEC.md` on startup
2. Parses port assignments from the specification
3. Validates each manifest port is allocated in the spec
4. **Refuses to register** services with unallocated ports
5. Shows error in Control Panel for invalid services

### Port Assignment Process

Before creating a service:

1. Check `docs/specs/PORT-ALLOCATION-SPEC.md` for available ports
2. Add your service to the spec FIRST
3. Create your service with the allocated port
4. Run validation: `python scripts/validate_ports.py`

### Reserved Port Ranges

| Range | Purpose |
|-------|---------|
| 9000-9009 | **Foundation Core** (DO NOT USE) |
| 9010-9019 | **Subscriber Services** |
| 9020-9029 | **Analysis Services** |
| 9030-9039 | **External Integrations** |
| 9222 | **Chrome CDP** (fixed by Chrome) |

---

## Service States

Services managed by Service Manager can be in one of these states:

| State | Description |
|-------|-------------|
| `stopped` | Service not running |
| `starting` | Process spawned, waiting for health check |
| `running` | Health check passing, service operational |
| `stopping` | SIGTERM sent, waiting for graceful shutdown |
| `error` | Failed to start or crashed |

### State Transitions

```
stopped ──start──> starting ──health_ok──> running
   ^                   │                      │
   │                   │                      │
   └──stop────────────┴──error──> error <────┘
```

---

## Health Endpoint Requirements

Every service MUST expose a health endpoint that:

1. Responds to HTTP GET at the configured `health_endpoint` path
2. Returns JSON with at least these fields:

```json
{
  "status": "healthy",
  "service": "service-name",
  "version": "1.0.0"
}
```

### Optional Health Fields

```json
{
  "status": "healthy",
  "service": "service-name",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "foundation_connected": true,
  "metrics": {
    "events_processed": 12500,
    "errors": 0
  }
}
```

### Health Check Behavior

- Service Manager polls health endpoint every 5 seconds
- Timeout: 3 seconds per request
- Service marked `error` after 3 consecutive failures
- First successful health check transitions `starting` → `running`

---

## Adding a New Service

### Checklist

1. [ ] **Allocate port** in `docs/specs/PORT-ALLOCATION-SPEC.md`
2. [ ] **Create directory** at `services/<name>/`
3. [ ] **Create manifest.json** with all required fields
4. [ ] **Implement health endpoint** returning required JSON
5. [ ] **Add start script** or entry point
6. [ ] **Write tests** in `services/<name>/tests/`
7. [ ] **Validate** with `python scripts/validate_ports.py`
8. [ ] **Document** in service README.md

### Directory Structure

```
services/<service-name>/
├── manifest.json       # REQUIRED: Service registration
├── README.md           # REQUIRED: Documentation
├── requirements.txt    # REQUIRED: Python dependencies
├── src/
│   ├── __init__.py
│   └── main.py         # Entry point matching start_command
├── config/
│   └── config.yaml     # Service configuration
├── tests/
│   └── test_*.py       # Unit tests
├── Dockerfile          # Optional: For containerized deployment
└── docker-compose.yml  # Optional: For containerized deployment
```

### Validation Script

```bash
# Validate all services
python scripts/validate_ports.py

# Validate specific service
python scripts/validate_ports.py --service recording
```

---

## Service Manager API

The Service Manager exposes these REST endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/services` | GET | List all registered services |
| `/api/services/<name>/start` | POST | Start a service |
| `/api/services/<name>/stop` | POST | Stop a service |
| `/api/services/<name>/status` | GET | Get detailed service status |

### Response Formats

**GET /api/services**
```json
{
  "services": [
    {
      "name": "recording-service",
      "status": "running",
      "port": 9010,
      "pid": 12345,
      "uptime_seconds": 3600
    }
  ]
}
```

**POST /api/services/<name>/start**
```json
{
  "success": true,
  "service": "recording-service",
  "status": "starting"
}
```

**POST /api/services/<name>/stop**
```json
{
  "success": true,
  "service": "recording-service",
  "status": "stopping"
}
```

---

## Enforcement Mechanisms

### 1. Service Manager Validation (Runtime)

- Validates manifest on service discovery
- Rejects services with invalid or missing manifests
- Reports errors in Control Panel UI

### 2. Port Validation Script (Development)

- `scripts/validate_ports.py` checks all manifests
- Fails if port not in PORT-ALLOCATION-SPEC
- Integrated into CI/CD pipeline

### 3. Hookify Rules (Development-time)

Located in `.claude/hookify.*.local.md`:
- Block services outside `services/` directory
- Block hardcoded ports
- Require manifest.json presence

### 4. Documentation Reference (Session persistence)

CLAUDE.md references this spec, ensuring every AI session sees these rules.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-24 | Initial specification |

---

**Every service MUST have a manifest. Every manifest MUST have a valid port. This is law.**
