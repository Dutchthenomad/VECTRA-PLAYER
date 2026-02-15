---
name: block-direct-cdp-websocket
enabled: true
event: file
pattern: CDPWebSocketInterceptor|cdp.*websocket|websocket.*cdp|chrome.*devtools.*websocket
action: block
---

# ARCHITECTURAL VIOLATION - BLOCKED

**You are attempting to write direct CDP WebSocket interception code.**

This pattern is **FORBIDDEN** in VECTRA-BOILERPLATE. It violates:
- **Rule 3**: NO custom WebSocket code in HTML
- **Rule 6**: NO direct WebSocket imports in Python
- **Architectural Principle**: All WebSocket events flow through Foundation Service

## The ONLY acceptable pattern:

```python
# Python: Inherit from BaseSubscriber
from foundation.subscriber import BaseSubscriber

class MyService(BaseSubscriber):
    def on_game_tick(self, event): ...
```

```javascript
// HTML: Use FoundationWSClient
import { FoundationWSClient } from '/shared/foundation-ws-client.js';
```

**DO NOT bypass Foundation Service. EVER.**

If you think you need direct CDP access, you are wrong. Discuss with the user first.
