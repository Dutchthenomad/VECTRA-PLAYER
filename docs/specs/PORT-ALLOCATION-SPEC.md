# VECTRA-BOILERPLATE Port Allocation Specification

**Status:** CANONICAL | **Version:** 1.0.0 | **Date:** 2026-01-19

---

## Purpose

This specification defines the **OFFICIAL** port allocations for all VECTRA services. These assignments are **PERMANENT** and **NON-NEGOTIABLE**.

**No service may use a port not assigned to it. No port may be reassigned without updating this spec.**

---

## Port Registry

### Reserved Ports (NEVER USE FOR ANYTHING ELSE)

| Port | Service | Protocol | Purpose | Owner |
|------|---------|----------|---------|-------|
| **9000** | Foundation WebSocket | WS | Event broadcast feed | `src/foundation/` |
| **9001** | Foundation HTTP | HTTP | Monitoring UI, health check | `src/foundation/` |
| **9010** | Recording Service | HTTP | Recording control API | `services/recording/` |
| **9016** | Rugs Feed Service | HTTP | Raw WebSocket capture API | `services/rugs-feed/` |
| **9017** | Rugs Sanitizer Service | HTTP/WS | Sanitized multi-channel feed | `services/rugs-sanitizer/` |
| **9222** | Chrome CDP | CDP | Chrome DevTools Protocol | Chrome browser |

### Future Allocations (Reserved, Not Yet Implemented)

| Port | Service | Protocol | Purpose | Status |
|------|---------|----------|---------|--------|
| **9011** | ML Training Subscriber | HTTP | ML data collection API | RESERVED |
| **9012** | RL Episode Subscriber | HTTP | RL episode tracking API | RESERVED |
| **9013** | Alert Service | HTTP | Alert/notification API | RESERVED |
| **9014** | Backtest Service | HTTP | Historical backtest API | RESERVED |
| **9015** | Strategy Service | HTTP | Strategy execution API | RESERVED |
| **9020** | Optimization Service | HTTP | Statistical analysis API | ALLOCATED |

### Port Ranges

| Range | Purpose |
|-------|---------|
| 9000-9009 | **Foundation Core** (DO NOT USE) |
| 9010-9019 | **Subscriber Services** |
| 9020-9029 | **Analysis Services** |
| 9030-9039 | **External Integrations** |
| 9222 | **Chrome CDP** (fixed by Chrome) |

---

## Environment Variables

All port configurations MUST be read from environment variables with these defaults:

```bash
# Foundation (NEVER CHANGE THESE DEFAULTS)
FOUNDATION_PORT=9000
FOUNDATION_HTTP_PORT=9001

# Chrome
CDP_PORT=9222

# Subscriber Services
RECORDING_PORT=9010
ML_TRAINING_PORT=9011
RL_EPISODE_PORT=9012
RUGS_FEED_PORT=9016
RUGS_SANITIZER_PORT=9017

# Analysis Services
ALERT_SERVICE_PORT=9013
BACKTEST_SERVICE_PORT=9014
STRATEGY_SERVICE_PORT=9015
OPTIMIZATION_SERVICE_PORT=9020
```

### Configuration File

Services should read from `config/ports.env` if it exists:

```bash
# config/ports.env - SINGLE SOURCE OF TRUTH
# DO NOT HARDCODE PORTS IN CODE

FOUNDATION_PORT=9000
FOUNDATION_HTTP_PORT=9001
CDP_PORT=9222
RECORDING_PORT=9010
```

---

## Rules

### Rule 1: No Hardcoded Ports

**WRONG:**
```python
server.bind(("localhost", 9000))  # Hardcoded - FORBIDDEN
```

**RIGHT:**
```python
import os
port = int(os.getenv("FOUNDATION_PORT", "9000"))
server.bind(("localhost", port))
```

### Rule 2: No Port Reassignment

If you need a new port:
1. Check this spec for available ports in the appropriate range
2. Add your service to this spec FIRST
3. Then implement

**DO NOT** reuse or reassign existing ports.

### Rule 3: Startup Validation

Every service MUST check if its port is available before binding:

```python
import socket

def check_port_available(port: int) -> bool:
    """Check if port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return True
        except OSError:
            return False

def validate_port_or_die(port: int, service_name: str):
    """Validate port is available, exit if not."""
    if not check_port_available(port):
        print(f"FATAL: Port {port} is already in use!")
        print(f"Service '{service_name}' cannot start.")
        print(f"Check: lsof -i :{port}")
        sys.exit(1)
```

### Rule 4: Foundation Ports Are Sacred

Ports 9000 and 9001 are **EXCLUSIVELY** for Foundation Service.

- No subscriber may bind to 9000 or 9001
- No artifact may connect to any WebSocket except ws://localhost:9000/feed
- No service may serve HTTP on 9001 except Foundation

---

## Conflict Resolution

If you encounter "address already in use":

### Step 1: Identify the culprit
```bash
lsof -i :9000
# or
ss -tlnp | grep 9000
```

### Step 2: Determine legitimacy

**If it's a VECTRA service:**
- Check if it should be running
- Stop it if duplicate

**If it's NOT a VECTRA service:**
- That service is violating this spec
- Stop it and configure it to use a different port

### Step 3: Prevent recurrence

- Add offending service to system startup exclusions
- Or configure it to use non-VECTRA port range

---

## Adding a New Service

1. **Check this spec** for next available port in appropriate range
2. **Update this spec** with your service's port assignment
3. **Create your service** reading port from environment variable
4. **Add to config/ports.env** the new variable
5. **Update CLAUDE.md** if it's a core service

---

## Enforcement

### Hookify Rules

`.claude/hookify.enforce-port-allocation.local.md` blocks:
- Hardcoded port 9000 or 9001 outside Foundation
- Port bindings not using environment variables

### CI/CD Validation

GitHub Actions checks:
- No hardcoded ports in new code
- All services use `os.getenv()` for port configuration

### Runtime Validation

`scripts/validate_ports.py`:
- Checks all expected ports are available
- Reports conflicts before starting services

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-19 | Initial specification |

---

**Port 9000 is Foundation. Foundation is Port 9000. This is law.**
