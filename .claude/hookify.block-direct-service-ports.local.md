---
name: block-direct-service-ports
enabled: true
event: file
pattern: localhost:901[0-9]|127\.0\.0\.1:901[0-9]
action: block
---

# ARCHITECTURAL VIOLATION - BLOCKED

**You are attempting to access service ports directly.**

This pattern is **FORBIDDEN** in VECTRA-BOILERPLATE artifacts.

## Why this is forbidden:

1. Service ports (9010-9019) are internal infrastructure
2. Artifacts should use Foundation's API proxy
3. Direct access bypasses authentication and rate limiting
4. Port allocation may change (see PORT-ALLOCATION-SPEC.md)

## The ONLY acceptable pattern:

**Use Foundation API proxy instead:**

```javascript
// FORBIDDEN - direct service access
fetch('http://localhost:9010/api/recordings');
fetch('http://127.0.0.1:9011/status');

// REQUIRED - use Foundation proxy
fetch('/api/recording/list');
fetch('/api/service/status');
```

## Port Reference:

| Port | Service | Access Method |
|------|---------|---------------|
| 9000 | Foundation WS | `ws://localhost:9000/feed` |
| 9001 | Foundation HTTP | `http://localhost:9001` (proxy) |
| 9010-9019 | Services | **Use /api/* proxy** |

**See: `docs/specs/PORT-ALLOCATION-SPEC.md`**
