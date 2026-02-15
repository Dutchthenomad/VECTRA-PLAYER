---
name: enforce-port-allocation
enabled: true
event: file
conditions:
  - field: file_path
    operator: not_regex_match
    pattern: src/foundation/
  - field: new_text
    operator: regex_match
    pattern: \b(9000|9001)\b.*\b(bind|listen|port|PORT)\b|\b(bind|listen|port|PORT)\b.*\b(9000|9001)\b
action: block
---

# PORT ALLOCATION VIOLATION - BLOCKED

**You are attempting to use port 9000 or 9001 outside of Foundation Service.**

Per `docs/specs/PORT-ALLOCATION-SPEC.md`:

> Ports 9000 and 9001 are **EXCLUSIVELY** for Foundation Service.
> - No subscriber may bind to 9000 or 9001
> - No service may serve HTTP on 9001 except Foundation

## Port Assignments

| Port | Service | Status |
|------|---------|--------|
| **9000** | Foundation WebSocket | **RESERVED - DO NOT USE** |
| **9001** | Foundation HTTP | **RESERVED - DO NOT USE** |
| 9010 | Recording Service | Available for recording |
| 9011-9019 | Subscriber Services | Available |

## How to Fix

1. Choose a port from the appropriate range (see PORT-ALLOCATION-SPEC.md)
2. Use environment variable, not hardcoded port:

```python
# WRONG
server.bind(("localhost", 9000))

# RIGHT
import os
port = int(os.getenv("YOUR_SERVICE_PORT", "9010"))
server.bind(("localhost", port))
```

3. Update PORT-ALLOCATION-SPEC.md with your port assignment

**Foundation owns 9000 and 9001. This is non-negotiable.**
