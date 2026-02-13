---
name: block-custom-websocket
enabled: true
event: file
pattern: new\s+WebSocket\(|websockets\.connect|websocket-client|import\s+websocket|from\s+websocket|ws://.*rugs\.fun|wss://.*rugs\.fun
action: block
---

# ARCHITECTURAL VIOLATION - BLOCKED

**You are attempting to write custom WebSocket connection code.**

This pattern is **FORBIDDEN** in VECTRA-BOILERPLATE. It violates:
- **Rule 3**: NO custom WebSocket code in HTML
- **Rule 6**: NO direct WebSocket imports in Python

## Why this is forbidden:

1. Foundation Service already handles WebSocket connection to rugs.fun
2. Foundation normalizes events to standard format
3. Foundation handles auth, reconnection, health checks
4. Custom code duplicates this logic and WILL drift

## The ONLY acceptable patterns:

**Python subscribers:**
```python
from foundation.subscriber import BaseSubscriber

class MySubscriber(BaseSubscriber):
    def on_game_tick(self, event):
        # Process normalized event
        pass
```

**HTML artifacts:**
```javascript
import { FoundationWSClient } from '/shared/foundation-ws-client.js';
const client = new FoundationWSClient('ws://localhost:9000/feed');
```

**NEVER connect directly to rugs.fun WebSocket. Use Foundation.**
