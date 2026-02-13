# VECTRA-BOILERPLATE Module Extension Specification

**Status:** CANONICAL | **Version:** 1.0.0 | **Date:** 2026-01-19

---

## Purpose

This specification defines the **ONLY** acceptable patterns for extending VECTRA-BOILERPLATE with new modules. All future development MUST follow these patterns. Deviations will be blocked by hookify rules and CI/CD validation.

**This document is referenced by CLAUDE.md and is binding on all AI agents and human developers.**

---

## Module Types

VECTRA-BOILERPLATE supports exactly three module types:

| Type | Location | Pattern | Purpose |
|------|----------|---------|---------|
| **HTML Artifact** | `src/artifacts/tools/<name>/` | Import shared resources | Browser-based UI tools |
| **Python Subscriber** | `src/subscribers/<name>/` | Inherit `BaseSubscriber` | Event consumers |
| **Docker Service** | `services/<name>/` | Docker Compose service | Containerized modules |

---

## Module Type 1: HTML Artifacts

### Directory Structure (REQUIRED)

```
src/artifacts/tools/<artifact-name>/
├── index.html          # Main entry point (REQUIRED)
├── manifest.json       # Module manifest (REQUIRED)
├── styles.css          # Local styles (OPTIONAL - extends shared)
└── app.js              # Local JavaScript (OPTIONAL)
```

### Required Imports (index.html)

Every HTML artifact MUST include these imports. No exceptions.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Artifact Name] - VECTRA</title>

    <!-- REQUIRED: Shared styles -->
    <link rel="stylesheet" href="../../shared/vectra-styles.css">
</head>
<body>
    <!-- Content here -->

    <!-- REQUIRED: Foundation WebSocket client -->
    <script type="module">
        import { FoundationWSClient } from '../../shared/foundation-ws-client.js';
        // Your code here
    </script>
</body>
</html>
```

### Required Manifest (manifest.json)

```json
{
  "name": "artifact-name",
  "version": "1.0.0",
  "description": "Brief description of what this artifact does",
  "author": "Your name",
  "created": "2026-01-19",
  "requires": {
    "foundation-ws-client": "^1.0.0",
    "vectra-styles": "^1.0.0"
  },
  "events_consumed": [
    "game.tick",
    "player.state"
  ],
  "api_endpoints": []
}
```

### FORBIDDEN Patterns (will be BLOCKED)

- `new WebSocket()` - Use `FoundationWSClient` instead
- `ws://` or `wss://` URLs to rugs.fun - Use Foundation feed
- Inline styles that duplicate `vectra-styles.css` variables
- Direct DOM manipulation without using semantic CSS classes

---

## Module Type 2: Python Subscribers

### Directory Structure (REQUIRED)

```
src/subscribers/<subscriber-name>/
├── __init__.py              # Package marker (REQUIRED)
├── subscriber.py            # Main subscriber class (REQUIRED)
├── config.py                # Configuration (OPTIONAL)
├── manifest.json            # Module manifest (REQUIRED)
└── tests/
    └── test_subscriber.py   # Unit tests (REQUIRED)
```

### Required Base Class

Every Python subscriber MUST inherit from `BaseSubscriber`. No exceptions.

```python
"""
<subscriber-name> - Brief description

This module follows VECTRA-BOILERPLATE MODULE-EXTENSION-SPEC v1.0.0
"""

from foundation.subscriber import BaseSubscriber
from foundation.events import GameTickEvent, PlayerStateEvent


class MySubscriber(BaseSubscriber):
    """
    Subscriber for [purpose].

    Consumed events:
        - game.tick: [why]
        - player.state: [why]
    """

    def __init__(self, client):
        super().__init__(client)
        # Your initialization here

    def on_game_tick(self, event: GameTickEvent) -> None:
        """Handle game tick events."""
        # Your logic here
        pass

    def on_player_state(self, event: PlayerStateEvent) -> None:
        """Handle player state events."""
        # Your logic here
        pass

    def on_connection_change(self, connected: bool) -> None:
        """Handle connection state changes."""
        # Your logic here
        pass
```

### Required Manifest (manifest.json)

```json
{
  "name": "subscriber-name",
  "version": "1.0.0",
  "description": "Brief description",
  "author": "Your name",
  "created": "2026-01-19",
  "requires": {
    "foundation": "^1.0.0",
    "python": ">=3.11"
  },
  "events_consumed": [
    "game.tick",
    "player.state"
  ],
  "api_endpoints": [
    "GET /subscriber-name/status",
    "POST /subscriber-name/start",
    "POST /subscriber-name/stop"
  ],
  "docker": {
    "enabled": true,
    "port": 9010,
    "health_endpoint": "/health"
  }
}
```

### FORBIDDEN Patterns (will be BLOCKED)

- `import websocket` or `import websockets` - Use `BaseSubscriber`
- `CDPWebSocketInterceptor` - Foundation handles this
- Direct connection to rugs.fun WebSocket
- Storing state in Foundation Service (use separate storage)

---

## Module Type 3: Docker Services

### Directory Structure (REQUIRED)

```
services/<service-name>/
├── Dockerfile               # Container definition (REQUIRED)
├── docker-compose.yml       # Service composition (REQUIRED)
├── src/                     # Source code
│   └── (subscriber or standalone code)
├── config/
│   └── config.yaml          # Configuration (REQUIRED)
├── manifest.json            # Module manifest (REQUIRED)
└── README.md                # Service documentation (REQUIRED)
```

### Required Dockerfile Pattern

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/
COPY config/ ./config/

# Health check (REQUIRED)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run service
CMD ["python", "-m", "src.main"]
```

### Required docker-compose.yml Pattern

```yaml
version: '3.8'

services:
  service-name:
    build: .
    container_name: vectra-service-name
    restart: unless-stopped
    ports:
      - "${PORT}:${PORT}"
    volumes:
      - ./config:/app/config:ro
      - ${DATA_PATH}:/data
    environment:
      - FOUNDATION_WS_URL=ws://host.docker.internal:9000/feed
      - PORT=${PORT}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - vectra-network

networks:
  vectra-network:
    external: true
```

### Required Health Endpoint

Every Docker service MUST expose a health endpoint:

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "service-name",
        "version": "1.0.0",
        "uptime_seconds": get_uptime(),
        "foundation_connected": client.is_connected
    }
```

---

## Creating a New Module: Checklist

### Before Starting

- [ ] Identify module type (HTML Artifact / Python Subscriber / Docker Service)
- [ ] Choose appropriate directory location per this spec
- [ ] Review existing modules of same type for patterns

### During Development

- [ ] Create directory structure per spec
- [ ] Create manifest.json with all required fields
- [ ] Import required shared resources (no custom WebSocket code)
- [ ] Inherit from BaseSubscriber (Python) or use FoundationWSClient (HTML)
- [ ] Add health endpoint (Docker services)
- [ ] Write unit tests

### Before Commit

- [ ] Run `scripts/validate_module.py <module-path>`
- [ ] Ensure all hookify rules pass
- [ ] Update docs/STATUS.md with new module
- [ ] Add module to appropriate index/registry

---

## Enforcement Mechanisms

### 1. Hookify Rules (Development-time)

Located in `.claude/hookify.*.local.md`, these rules BLOCK:
- Custom WebSocket code
- Direct CDP interception
- Missing shared resource imports
- Incorrect directory locations

### 2. CI/CD Validation (Pre-merge)

GitHub Actions workflow validates:
- Directory structure compliance
- Manifest.json presence and validity
- Required imports present
- Tests exist and pass

### 3. Documentation Reference (Session persistence)

CLAUDE.md references this spec, ensuring every AI session sees these rules.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-19 | Initial specification |

---

## Questions?

If a pattern isn't covered here, it's probably not allowed. When in doubt:
1. Check existing modules of the same type
2. Ask before implementing non-standard patterns
3. Update this spec if a new pattern is approved

**DO NOT deviate from this spec without explicit approval and spec update.**
